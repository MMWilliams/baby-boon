"""Checked facts for one turn, appended to the system prompt. Pilots v4-v13 got short trivia right but kitchen
conversions wrong (quarter cup = "2 tablespoons", 1 lb butter = "1/4 cup") and invented animal facts on request; a 1.7B
model can't be trained into arithmetic, so conversions are computed and fun facts come from a checked list."""
import re
import zlib

# Size in ml or g.
UNITS = {"teaspoon": ("volume", 4.92892), "tablespoon": ("volume", 14.7868), "fluid ounce": ("volume", 29.5735),
         "cup": ("volume", 236.588), "pint": ("volume", 473.176), "quart": ("volume", 946.353),
         "gallon": ("volume", 3785.41), "milliliter": ("volume", 1), "liter": ("volume", 1000), "stick": ("volume", 118.294),
         "ounce": ("weight", 28.3495), "pound": ("weight", 453.592), "gram": ("weight", 1), "kilogram": ("weight", 1000),
         "°F": ("temperature", 1), "°C": ("temperature", 1)}
# Grams per US cup, so volume and weight convert for named ingredients. Butter: 1 cup = 8 oz, 1 stick = 1/2 cup = 4 oz.
INGREDIENTS = {"butter": 226.796, "peanut butter": 258, "flour": 125, "sugar": 200, "brown sugar": 220,
               "powdered sugar": 120, "honey": 340, "water": 236.588, "milk": 245, "cream": 240, "yogurt": 245,
               "oil": 218, "rice": 185, "oats": 90, "cocoa": 85, "salt": 288}
LIQUIDS = {"water", "milk", "cream", "oil"}  # "ounces" of these means fluid ounces
DEFAULTS = {"volume": ("tablespoon", "cup", "fluid ounce"), "weight": ("ounce", "pound"),
            "butter": ("stick", "cup", "tablespoon", "ounce"), "temperature": ("°F", "°C")}
# Longer spellings first where they share a start ("fl oz" before "f"). Single letters count only after a digit.
ALIASES = [(r"fluid ounces?|fl\.? ?oz", "fluid ounce"), (r"teaspoons?|tsps?", "teaspoon"),
           (r"tablespoons?|tbsps?|tbs", "tablespoon"), (r"cups?", "cup"), (r"pints?", "pint"), (r"quarts?|qts?", "quart"),
           (r"gallons?|gal", "gallon"), (r"millilit(?:er|re)s?|mls?", "milliliter"), (r"lit(?:er|re)s?", "liter"),
           (r"sticks?", "stick"), (r"ounces?|oz", "ounce"), (r"pounds?|lbs?", "pound"),
           (r"kilograms?|kilos?|kgs?", "kilogram"), (r"grams?|g", "gram"), (r"fahrenheit|farenheit|f", "°F"),
           (r"celsius|celcius|centigrade|c", "°C")]
UNIT = "|".join(f"(?:{alias})" for alias, _ in ALIASES)
GLYPHS = {"½": 1/2, "¼": 1/4, "¾": 3/4, "⅓": 1/3, "⅔": 2/3, "⅛": 1/8}
WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
         "nine": 9, "ten": 10, "twelve": 12, "half": 1/2, "halves": 1/2, "third": 1/3, "thirds": 1/3, "quarter": 1/4,
         "quarters": 1/4, "eighth": 1/8, "eighths": 1/8}
COUNT = r"a|an|one|two|three|four|five|six|seven|eight|nine|ten|twelve"
PART = r"halves|half|thirds?|quarters?|eighths?"
NUMBER = r"\d+(?:\.\d+)?(?:\s*[½¼¾⅓⅔⅛]|\s+\d+/\d+)?|\d+/\d+"
AMOUNT = rf"{NUMBER}|[½¼¾⅓⅔⅛]|(?:(?:{COUNT})[\s-])?(?:{PART})|(?:{COUNT})(?:\s+and\s+a\s+half)?"
QUANTITY = re.compile(rf"(?<![\w/.])({AMOUNT})(?:\s+of\s+an?|\s+an?|\s+in)?\s*(?:°\s*|degrees?\s+)?({UNIT})\b", re.I)
# Unit first, then a bare reading: "the thermometer is on celsius and reads 38.5".
UNIT_FIRST = re.compile(rf"(?<![\w°])({UNIT})\b(?:\s+\w+){{0,2}}?\s+(?:reads?|says?|shows?|is|at|=)\s*({NUMBER})(?![\w/]|\.\d)", re.I)
UNIT_WORD = re.compile(rf"(?<![\w°])(?:{UNIT})\b", re.I)
LETTER_TARGET = re.compile(r"\b(?:in|to|into|does|uses|shows|reads|on)\s+([CF])\b", re.I)
INGREDIENT = "|".join(sorted(INGREDIENTS, key=len, reverse=True)).replace(" ", r"\s+")
AFTER = re.compile(rf"\s+(?:of\s+)?(?:[\w-]+\s+)??({INGREDIENT})\b", re.I)
BEFORE = re.compile(rf"\b({INGREDIENT})\W{{0,3}}$", re.I)
ASK = re.compile(r"\bconvert|\bhow (?:many|much)\b|\bwhat(?:'s|s| is) (?:that|this|it)\b|\bequals?\b|\bsame as\b", re.I)
FRACTION = {1/8: "1/8", 1/4: "1/4", 1/3: "1/3", 3/8: "3/8", 1/2: "1/2", 5/8: "5/8", 2/3: "2/3", 3/4: "3/4", 7/8: "7/8"}
NICE = (0, *FRACTION, 1)

FACTS = {
    "ocean": ["Starfish don't have blood; they pump seawater through their bodies instead.",
              "A blue whale's heart weighs about 400 pounds.",
              "Sea otters sometimes hold paws while floating so they don't drift apart.",
              "One jellyfish species, Turritopsis dohrnii, can turn back into a younger stage of its life.",
              "Sharks are older than trees: sharks appeared over 400 million years ago, trees around 385 million.",
              "Most of the ocean floor still hasn't been mapped in high detail."],
    "animal": ["Octopuses have three hearts: two pump blood through the gills and one pumps it to the rest of the body.",
               "Wombats make cube-shaped poop.", "Hummingbirds can fly backwards.",
               "Butterflies taste with sensors on their feet.",
               "Crows can recognize individual human faces and remember them for years.",
               "Cats can't taste sweetness; their sweet-taste receptor gene doesn't work.",
               "Owls can't move their eyes, so they turn their heads instead, up to about 270 degrees.",
               "Axolotls can regrow lost legs, and even parts of their heart and spinal cord.",
               "Male seahorses carry the eggs and give birth to the babies.",
               "A group of flamingos is called a flamboyance.", "Polar bears have black skin under their fur.",
               "Goats have rectangular pupils, which give them a wide view for spotting predators.",
               "Dolphins can sleep with one half of their brain at a time."],
    "space": ["A day on Venus is longer than its year: one spin takes 243 Earth days, one trip around the Sun about 225.",
              "Sunlight takes about 8 minutes to reach Earth.", "Saturn is less dense than water on average.",
              "One year on Neptune lasts about 165 Earth years.",
              "Earth has about 3 trillion trees, more than the 100 to 400 billion stars in the Milky Way.",
              "Jupiter's Great Red Spot is a storm wider than Earth.",
              "Olympus Mons on Mars is about two and a half times as tall as Mount Everest."],
    "body": ["Babies are born with about 270 to 300 bones and cartilage pieces; many fuse, leaving adults with 206.",
             "Your brain is about 2 percent of your body weight but uses about 20 percent of its energy at rest.",
             "The cells lining your stomach replace themselves every few days.",
             "Your heart beats about 100,000 times a day.",
             "You're slightly taller in the morning, because the discs in your spine compress during the day.",
             "Humans give off a very faint glow, about 1,000 times too weak for our eyes to see."],
    "food": ["Botanically, bananas are berries, but strawberries aren't.",
             "Peanuts aren't nuts; they're legumes, like beans and peas.",
             "Sealed honey basically never spoils, because it has too little water for microbes to grow.",
             "A pineapple plant takes about two years to grow a single pineapple.",
             "Carrots weren't always orange; early farmed carrots were mostly purple or yellow.",
             "Cashews grow hanging from the bottom of a fruit called the cashew apple."],
}
TOPICS = {"ocean": r"ocean|sea|marine|underwater|fish", "animal": r"animals?|creatures?|birds?|bugs?|insects?|pets?|dogs?|cats?",
          "space": r"space|planets?|stars?|moon|sun|galax\w*|universe", "body": r"body|brain|bones?|human|heart|blood",
          "food": r"food|fruits?|veg\w*|cooking|snacks?"}
# Words in the facts above that don't name a subject (stripped of a trailing s before matching).
GENERIC = {"about", "than", "that", "this", "with", "from", "have", "into", "more", "most", "over", "back", "some", "only",
           "even", "much", "many", "like", "when", "what", "their", "there", "these", "those", "which", "while", "still",
           "other", "every", "through", "instead", "around", "because", "during", "time", "where", "thing", "something",
           "anything", "year", "long", "part", "high", "under", "give", "turn", "hold", "make", "called", "group", "weak",
           "faint", "very", "body", "human", "about", "tell", "know", "fact", "trivia", "weird", "cool", "mind"}
ADJ = (r"fun|weird|cool|random|interesting|wild|strange|crazy|odd|neat|surprising|bizarre|unusual|amazing|creepy|gross"
       r"|science|animal|space|ocean|food|body")
MOST = (r"weirdest|coolest|strangest|craziest|wildest|oddest|creepiest|grossest|funniest"
        r"|most (?:interesting|surprising|random|bizarre|unusual|amazing)")
PERSONAL = r"me|my|you|your|yourself|him|his|her|them|their|us|our"
FACT_REQUEST = re.compile(
    rf"\b(?:{ADJ})(?:[ -]\w+)? facts?\b|\bfacts? about\b|\b(?:tell|give|teach|share|hit|drop|send)\b[^.?!]{{0,25}}\bfacts?\b"
    rf"|\b(?:any|some|random|quick)(?: \w+)? (?:facts?|trivia)\b|\bblow my mind\b"
    # "what's the weirdest thing about the human body", but not "...about your day"
    rf"|\b(?:what(?:'s|s| is)|tell me|hit me with|give me)(?: the)? (?:{MOST}) (?:thing|part|stuff|bit|creature|animal)s?\b"
    rf"(?!(?: (?:about|in|with|for))? (?:{PERSONAL})\b)"
    # Without a lead, only as a question: "most surprising thing about the human body?"
    rf"|\b(?:{MOST}) (?:thing|part|stuff|bit)s? about (?!(?:{PERSONAL})\b)[^.?!]{{0,30}}\?"
    # "say something interesting", but not "...about yourself"
    rf"|\b(?:say|tell me|share|give me|teach me|distract me with|hit me with|know) something "
    rf"(?:{ADJ}|i (?:don'?t|didn'?t) know)\b(?! about (?:{PERSONAL})\b)",
    re.I)
CONVERSION_LEAD = "For this reply, use these checked numbers exactly and add no other figures:"
FACT_LEAD = "For this reply, share this checked fact in your own words and add no other facts:"


def canonical(word):
    return next(unit for alias, unit in ALIASES if re.fullmatch(alias, word, re.I))


def ratio(text):
    top, _, bottom = text.partition("/")
    return float(top) / float(bottom or 1)


def amount(text):
    text = text.lower()
    if text in GLYPHS: return GLYPHS[text]
    if text[0].isdigit():
        whole, glyph, fraction = re.fullmatch(r"(\d+(?:\.\d+)?|\d+/\d+)\s*([½¼¾⅓⅔⅛]?)\s*(\d+/\d+)?", text).groups()
        return ratio(whole) + (ratio(fraction) if fraction else 0) + GLYPHS.get(glyph, 0)
    words = re.split(r"[\s-]+", text)
    if "and" in words: return WORDS[words[0]] + 0.5  # "one and a half"
    if words[-1] in ("half", "halves", "third", "thirds", "quarter", "quarters", "eighth", "eighths"):
        return WORDS[words[-1]] * (WORDS[words[0]] if len(words) > 1 else 1)
    return WORDS[words[0]]


def number(x):
    """Whole numbers and common fractions when within 1%, else rounded; "about" when the shown value isn't exact."""
    whole, part = divmod(x, 1)
    nice = min(NICE, key=lambda f: abs(part - f))
    if x < 20 and abs(whole + nice - x) <= 0.01 * x:
        whole, shown = int(whole + (nice == 1)), whole + nice
        text = " ".join(s for s in (str(whole) if whole or nice in (0, 1) else "", FRACTION.get(nice, "")) if s)
    else:
        shown = round(x) if x >= 20 else round(x, 1)
        text = f"{shown:,}" if x >= 20 else f"{shown:g}"
    return ("about " if abs(shown - x) > 0.01 else "") + text


def label(value, unit, rough=False):
    if unit.startswith("°"): return f"{round(value, 1):g}{unit}"
    text = f"{number(value)} {unit}{'' if value <= 1 else 's'}"
    return text if text.startswith("about") or not rough else "about " + text


def convert(value, unit, target, ingredient):
    if unit.startswith("°"): return value * 9 / 5 + 32 if target == "°F" else (value - 32) * 5 / 9
    (dim, size), (target_dim, target_size) = UNITS[unit], UNITS[target]
    base = value * size
    if dim != target_dim:
        density = INGREDIENTS[ingredient] / UNITS["cup"][1]
        base = base * density if dim == "volume" else base / density
    return base / target_size


def compatible(unit, target, ingredient):
    dims = {UNITS[unit][0], UNITS[target][0]}
    return unit != target and (len(dims) == 1 or (ingredient and dims == {"volume", "weight"}))


def ingredient_of(user, span, unit):
    if unit == "stick": return "butter"
    m = AFTER.match(user, span[1]) or BEFORE.search(user[:span[0]])
    return re.sub(r"\s+", " ", m[1].lower()) if m else None


def inside(found, pos):
    return any(start <= pos < end for (start, end), *_ in found)


def parse(user):
    """(value, unit, ingredient) amounts in the message, and the units it asks for."""
    found = []  # (span, amount text, unit)
    for m in QUANTITY.finditer(user):
        word = m[2]
        if len(word) == 1 and not (m[1][0].isdigit() and (word in ("C", "F", "g") or "°" in m[0] or "degree" in m[0].lower())):
            continue
        found.append((m.span(), m[1], canonical(word)))
    for m in UNIT_FIRST.finditer(user):
        if (len(m[1]) > 1 or re.search(r"\bin\s*$", user[:m.start()], re.I)) and not inside(found, m.start(2)):
            found.append((m.span(), m[2], canonical(m[1])))
    # Next to a real amount, "a teaspoon" names the measure wanted ("need 2 tbsp, only have a teaspoon").
    named = [q for q in found if q[1].lower() in ("a", "an")]
    if len(named) == len(found): named = []
    targets = [unit for _, _, unit in named]
    for m in UNIT_WORD.finditer(user):
        unit = canonical(m[0])
        if (len(m[0]) > 1 and unit not in targets and not inside(found, m.start())
                and (unit != "stick" or re.search(r"\bbutter\b", user, re.I))):
            targets.append(unit)
    for m in LETTER_TARGET.finditer(user):  # "what's that in F"
        unit = canonical(m[1])
        if unit not in targets and not inside(found, m.start(1)): targets.append(unit)
    return [(amount(text), unit, ingredient_of(user, span, unit)) for span, text, unit in found
            if (span, text, unit) not in named], targets


def line(value, unit, ingredient, targets):
    if ingredient in LIQUIDS and UNITS[unit][0] == "volume":
        targets = ["fluid ounce" if t == "ounce" else t for t in targets]
    chosen = [t for t in targets if compatible(unit, t, ingredient)]
    if targets and not chosen:
        return (f"{label(value, unit)} can't be converted to {targets[0]}s without knowing the ingredient; "
                "a kitchen scale or the package label is safest.")
    defaults = DEFAULTS["butter" if ingredient == "butter" and not unit.startswith("°") else UNITS[unit][0]]
    chosen = chosen or [t for t in defaults if compatible(unit, t, ingredient)]
    rough = ingredient not in (None, "butter", "water")  # cup weights of flour, sugar etc. vary with packing
    return " = ".join([label(value, unit) + (f" of {ingredient}" if ingredient and unit != "stick" else "")]
                      + [label(convert(value, unit, t, ingredient), t, rough and UNITS[unit][0] != UNITS[t][0])
                         for t in chosen]) + "."


def conversion_note(user):
    quantities, targets = parse(user)
    asked = bool(ASK.search(user))
    # The source unit named again ("my 1/3 measuring cup ... how many tablespoons") isn't a target.
    notes = [line(value, unit, ingredient, [t for t in targets if t != unit]) for value, unit, ingredient in quantities
             if asked or any(t != unit for t in targets)]
    return " ".join(dict.fromkeys(notes)) or None  # the same amount said twice gets one line


def fact_note(user):
    if not FACT_REQUEST.search(user): return None
    topic = next((t for t, words in TOPICS.items() if re.search(rf"\b(?:{words})\b", user, re.I)), None)
    pool = FACTS[topic] if topic else [fact for facts in FACTS.values() for fact in facts]
    # A named subject ("about octopuses") picks a fact that mentions it; otherwise the model answers on its own.
    words = {w.rstrip("s") for w in re.findall(r"[a-z]{4,}", user.lower())} - GENERIC
    pool = [fact for fact in pool if any(w in fact.lower() for w in words)] or pool
    return pool[zlib.crc32(user.encode()) % len(pool)]


def with_facts(messages, user):
    """messages with this turn's checked facts appended to the system prompt; unchanged when there are none."""
    notes = [f"{lead} {note}" for lead, note in ((CONVERSION_LEAD, conversion_note(user)), (FACT_LEAD, fact_note(user))) if note]
    if not notes: return messages
    return [{**messages[0], "content": messages[0]["content"] + " " + " ".join(notes)}] + messages[1:]
