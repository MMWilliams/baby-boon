"""Checked facts for one turn, appended to the system prompt. Pilots v4-v13 got short trivia right but kitchen
conversions wrong (quarter cup = "2 tablespoons", 1 lb butter = "1/4 cup") and invented animal facts on request; a 1.7B
model can't be trained into arithmetic, so conversions are computed and fun facts come from a checked list."""
import re
import zlib

# Size in ml or g. Butter converts between volume and weight at 1 cup = 8 oz, so 1 stick = 1/2 cup = 4 oz.
UNITS = {"teaspoon": ("volume", 4.92892), "tablespoon": ("volume", 14.7868), "fluid ounce": ("volume", 29.5735),
         "cup": ("volume", 236.588), "pint": ("volume", 473.176), "quart": ("volume", 946.353),
         "gallon": ("volume", 3785.41), "milliliter": ("volume", 1), "liter": ("volume", 1000), "stick": ("volume", 118.294),
         "ounce": ("weight", 28.3495), "pound": ("weight", 453.592), "gram": ("weight", 1), "kilogram": ("weight", 1000),
         "°F": ("temperature", 1), "°C": ("temperature", 1)}
BUTTER_G_PER_ML = 226.796 / 236.588
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
AMOUNT = (rf"\d+(?:\.\d+)?(?:\s*[½¼¾⅓⅔⅛]|\s+\d+/\d+)?|\d+/\d+|[½¼¾⅓⅔⅛]"
          rf"|(?:(?:{COUNT})[\s-])?(?:{PART})|(?:{COUNT})(?:\s+and\s+a\s+half)?")
QUANTITY = re.compile(rf"(?<![\w/.])({AMOUNT})(?:\s+of\s+an?|\s+an?)?\s*(?:°\s*|degrees?\s+)?({UNIT})\b", re.I)
UNIT_WORD = re.compile(rf"(?<![\w°])(?:{UNIT})\b", re.I)
ASK = re.compile(r"\bconvert|\bhow (?:many|much)\b|\bwhat(?:'s| is) (?:that|this|it)\b|\bequals?\b|\bsame as\b", re.I)
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
FACT_REQUEST = re.compile(
    r"\b(?:fun|weird|cool|random|interesting|wild|strange|crazy|odd|neat|surprising|science|animal|space|ocean|food|body)"
    r"(?:[ -]\w+)? facts?\b|\bfacts? about\b|\b(?:tell|give|teach|share|hit|drop|send)\b[^.?!]{0,25}\bfacts?\b"
    r"|\bany (?:good |fun )?facts?\b", re.I)
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
    if words[-1] in ("half", "halves", "third", "thirds", "quarter", "quarters", "eighth", "eighths"):
        return WORDS[words[-1]] * (WORDS[words[0]] if len(words) > 1 else 1)
    return WORDS[words[0]] + (0.5 if "half" in words else 0)


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


def label(value, unit):
    if unit.startswith("°"): return f"{round(value, 1):g}{unit}"
    return f"{number(value)} {unit}{'' if value <= 1 else 's'}"


def convert(value, unit, target):
    if unit.startswith("°"): return value * 9 / 5 + 32 if target == "°F" else (value - 32) * 5 / 9
    (dim, size), (target_dim, target_size) = UNITS[unit], UNITS[target]
    base = value * size
    if dim != target_dim: base = base * BUTTER_G_PER_ML if dim == "volume" else base / BUTTER_G_PER_ML
    return base / target_size


def compatible(unit, target, butter):
    dims = {UNITS[unit][0], UNITS[target][0]}
    return unit != target and (len(dims) == 1 or (butter and dims == {"volume", "weight"}))


def parse(user):
    """(value, unit, butter) amounts in the message, and the units it asks for."""
    found = []
    for m in QUANTITY.finditer(user):
        word = m[2]
        if len(word) == 1 and not (m[1][0].isdigit() and (word in ("C", "F", "g") or "°" in m[0] or "degree" in m[0].lower())):
            continue
        unit = canonical(word)
        butter = unit == "stick" or bool(re.match(r"\s+(?:of\s+)?(?:\w+\s+)?butter\b", user[m.end():], re.I)
                                         or re.search(r"\bbutter\W{0,3}$", user[:m.start()], re.I))
        found.append((m, unit, butter))
    # Next to a real amount, "a teaspoon" names the measure wanted ("need 2 tbsp, only have a teaspoon").
    named = [q for q in found if q[0][1].lower() in ("a", "an")]
    if len(named) == len(found): named = []
    targets = [unit for _, unit, _ in named]
    for m in UNIT_WORD.finditer(user):
        unit = canonical(m[0])
        if (len(m[0]) > 1 and unit not in targets and not any(q.start() <= m.start() < q.end() for q, *_ in found)
                and (unit != "stick" or re.search(r"\bbutter\b", user, re.I))):
            targets.append(unit)
    return [(amount(m[1]), unit, butter) for m, unit, butter in found if (m, unit, butter) not in named], targets


def line(value, unit, butter, targets):
    chosen = [t for t in targets if compatible(unit, t, butter)]
    if targets and not chosen:
        return (f"{label(value, unit)} can't be converted to {targets[0]}s without knowing the ingredient; "
                "a kitchen scale or the package label is safest.")
    defaults = DEFAULTS["butter" if butter and not unit.startswith("°") else UNITS[unit][0]]
    chosen = chosen or [t for t in defaults if compatible(unit, t, butter)]
    return " = ".join([label(value, unit) + (" of butter" if butter and unit != "stick" else "")]
                      + [label(convert(value, unit, t), t) for t in chosen]) + "."


def conversion_note(user):
    quantities, targets = parse(user)
    if not (targets or ASK.search(user)): return None
    return " ".join(line(value, unit, butter, targets) for value, unit, butter in quantities if unit not in targets) or None


def fact_note(user):
    if not FACT_REQUEST.search(user): return None
    topic = next((t for t, words in TOPICS.items() if re.search(rf"\b(?:{words})\b", user, re.I)), None)
    pool = FACTS[topic] if topic else [fact for facts in FACTS.values() for fact in facts]
    return pool[zlib.crc32(user.encode()) % len(pool)]


def with_facts(messages, user):
    """messages with this turn's checked facts appended to the system prompt; unchanged when there are none."""
    notes = [f"{lead} {note}" for lead, note in ((CONVERSION_LEAD, conversion_note(user)), (FACT_LEAD, fact_note(user))) if note]
    if not notes: return messages
    return [{**messages[0], "content": messages[0]["content"] + " " + " ".join(notes)}] + messages[1:]
