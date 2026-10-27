"""Health guard. facts3 h22: a parent asked what 38.7°C is in Fahrenheit and v12 answered "it's not dangerous ... take a
fever pill". A 1.7B model can't dose a medicine, judge a fever or diagnose, so in a health context a reply may not do
those; it may still convert, comfort, suggest rest and fluids and point to a pharmacist, doctor or nurse line (the
authored first-aid rows do). Red-flag messages skip the model's judgment and get the emergency line. Three tiers, as in a
risk-based policy: answer normally outside a health context, answer without the advice inside one, escalate on red flags."""
import re

NAMED = (r"paracetamol|acetaminophen|tylenol|calpol|ibuprofen|advil|motrin|nurofen|aspirin|benadryl|antihistamines?|zyrtec|claritin"
         r"|piriton|nyquil|dayquil|sudafed|decongestants?|pepto|imodium|loperamide|tums|antacids?|melatonin|codeine|naproxen|aleve"
         r"|antibiotics?|steroids?")
MEDICAL = (rf"fever(?:ish|s)?|thermometer|(?:has|have|had|got|running) a temperature|sick(?! of\b| and tired\b)|unwell|flu(?:ish)?"
           r"|cough(?:ing|s)?|vomit\w*|throw(?:ing|n|s)? up|threw up|puk(?:e|ed|ing)|diarrh\w+|rash(?:es)?|hives|migraines?|nause\w+"
           r"|dizzy|dizziness|fainted|fainting|allerg\w+|asthma|inhaler|wheez\w+|infection|infected|sore throat|earache|toothache"
           r"|teething|pregnan\w+|symptoms?|dehydrated|concussion|sprain(?:ed)?|stitches|blister\w*|doses?|dosage|medicine|medication"
           rf"|meds|pills?|tablets?|painkillers?|{NAMED}|pharmacist|pharmacy|doctor|pediatrician|paediatrician|gp|nurse|urgent care|er|a&e"
           r"|hospital|ambulance|first aid|bleeding|nosebleed|chest pains?|stomach ?ache|tummy ache|belly ache|cramps|hangover|hungover"
           r"|burn(?:ed|t) (?:my|his|her|their|your) (?:hand|finger|fingers|arm|leg|foot|face|tongue|mouth|skin|wrist|palm|thumb)")
# Figurative uses: "giving me a headache", "makes me sick", "that beat is sick", "a dose of good news".
FIGURATIVE = re.compile(
    r"\bgiv(?:e|es|ing) (?:me|us|him|her|them) a headache\b|\bmakes? me sick\b|\bthat'?s sick\b|\bsick(?:est)? (?:beat|drop|track|move|skills?)\b"
    r"|\b(?:beat|track|song|drop|move|trick|game|car|bike|fit|shoes|kicks|skills?) (?:is|was|are|looks?|sounds?) (?:so |pretty |really )?sick\b"
    r"|\bdoses? of (?:good news|bad news|reality|sunshine|humou?r|fresh air|perspective|cute\w*)\b", re.I)
HEADACHE = re.compile(r"\bheadaches?\b", re.I)
# A body-range reading with its scale (35-42°C, 95-107°F), or "temp of 38.2".
BODY_READING = re.compile(
    r"\b(?:3[5-9]|4[0-2])(?:\.\d)?\s*(?:°\s*|degrees?\s+)?(?:c|celsius|celcius|centigrade)\b|\b(?:9[5-9]|10[0-7])(?:\.\d)?\s*(?:°\s*|degrees?\s+)?(?:f|fahrenheit|farenheit)\b"
    r"|\b(?:celsius|celcius|fahrenheit|thermometer)\b[^.?!]{0,30}?\b(?:3[5-9]|4[0-2]|9[5-9]|10[0-7])(?:\.\d)?\b"
    r"|\btemp(?:erature)?(?:'s)? (?:of|is|was|at|reads|says|hit|went up to) (?:a |about |around )?(?:3[5-9]|4[0-2]|9[5-9]|10[0-7])(?:\.\d)?\b", re.I)
CONTEXT = re.compile(rf"\b(?:{MEDICAL})\b", re.I)
RED_FLAG = re.compile(
    r"\b(?:not breathing|stopped breathing|struggling to breathe|trouble breathing|can'?t breathe properly|gasping|turning blue"
    r"|blue lips|lips are blue|unresponsive|unconscious|won'?t wake up(?! for\b| before\b| until\b| in time)"
    r"|can'?t wake (?:him|her|them|the baby|my \w+)|hard to wake|seizure|seizing|convuls\w+"
    r"|overdos\w+(?! on (?:coffee|caffeine|sugar|netflix|tv|memes|cuteness|work))"
    r"|took (?:too many|a bunch of|a handful of|(?:a|the) whole bottle of|all (?:the|her|his|my|their)) (?:[\w']+ ){0,2}?(?:pills|tablets|meds|medicine|medication|paracetamol|tylenol|ibuprofen)"
    r"|swallowed (?:a|an|some|the|her|his|my|one of) (?:[\w']+ )?(?:battery|batteries|magnets?|pills|tablets|bleach|cleaner|coins?|detergent|pods?)"
    r"|chest pains?|having a stroke|slurred speech|speech is slurred|slurring (?:her|his|their) (?:words|speech)|face is drooping"
    r"|anaphyla\w+|throat (?:is )?(?:closing|swelling)|severe bleeding|won'?t stop bleeding|bleeding (?:a lot|heavily|everywhere)"
    r"|asthma attack|no pulse)\b", re.I)
# Only with another health cue: "laughing so hard I can't breathe" is not an emergency, a stiff neck needs a fever beside it.
BREATHING = re.compile(r"\b(?:can'?t|cannot|hard to|difficulty|trouble|struggling to) breath(?:e|ing)\b", re.I)
STIFF_NECK = re.compile(r"\bstiff neck\b", re.I)
FEVER = re.compile(r"\b(?:fever(?:ish)?|temp(?:erature)?|burning (?:up|hot)|thermometer)\b", re.I)

DRUG = (rf"{NAMED}|cough (?:syrup|medicine|drops)|fever (?:reducer|medicine|pills?|tablets?)|pain ?killers?"
        r"|pain (?:meds|relief|relievers?)|pills?|tablets?|capsules?|medicine|medication|meds|(?:eye|ear|nose) drops|ointment"
        r"|(?<!ice )cream|supplements?|vitamins?")
SUGGEST = re.compile(
    rf"\b(?:take|takes|taking|took|give|gives|giving|try|trying|use|using|pop|popping|grab|get|have|need|needs|start|starting|a dose of|some)\b"
    rf"[^.?!]{{0,40}}?\b(?:{DRUG})\b"
    rf"|\b(?:{DRUG})\b[^.?!]{{0,25}}?\b(?:helps?|works?|will|would|should|can|brings?|lowers?|reduces?|eases?|settles?|clears?|fixes?|does the trick)\b"
    r"|\b\d+(?:\.\d+)?\s?(?:mg|milligrams?|mcg|micrograms?)\b|\bevery (?:\d+|two|three|four|six|eight|twelve) (?:to \d+ )?hours\b", re.I)
# A pointer to a professional may mention medicines ("ask the pharmacist which medicine fits").
DEFERS = re.compile(r"\b(?:ask|check with|call|ring|phone|see|talk to|speak to|consult)\b[^.?!]{0,30}?\b(?:pharmacist|pharmacy|doctor|gp|nurse|pediatrician|paediatrician|clinic)\b", re.I)
DIAGNOSIS = (r"strep|an? (?:ear|sinus|chest|throat|urinary|kidney|bladder) infection|appendicitis|meningitis|pneumonia|bronchitis"
             r"|covid|the flu|a virus|a (?:stomach |tummy )?bug|a cold|allergies|a migraine|food poisoning|dehydration|teething"
             r"|growing pains|anxiety|a panic attack|a sprain|a fracture|broken|concussion|reflux|heartburn|a tension headache|hay ?fever")
VERDICT = re.compile(
    r"\b(?:isn'?t|is not|not|nothing|it'?s not|that'?s not) (?:really |that |too |very |at all )?(?:dangerous|serious|a big deal|anything to worry about|an emergency|urgent|a concern)\b"
    r"|\bnothing to worry about\b|\bno (?:need|reason) to (?:worry|panic|see a doctor|call (?:a|the) doctor|go to the (?:er|hospital|doctor))\b"
    r"|\bdon'?t (?:need to )?(?:worry|panic)\b(?! about (?!(?:it|that|him|her|them)\b))"
    r"|\b(?:you|he|she|they|the (?:baby|kid|kiddo|little one|kids))(?:'ll be| will be|'re| are|'s| is) (?:going to be |gonna be |totally |perfectly |completely |just |probably )?(?:fine|okay|ok|safe|all ?right)\b(?! to\b| if\b| with\b| as\b)"
    r"|\b(?:it|that|this)(?:'ll be| will be|'s going to be| is going to be|'s gonna be) (?:totally |perfectly |completely |just |probably )?(?:fine|okay|ok|all ?right)\b"
    r"|\b(?:perfectly|totally|completely) (?:normal|safe|fine)\b(?! to\b)|\b(?:should|will|it'?ll|that'?ll) (?:pass|clear up|go away|settle(?: down)?|be gone)\b"
    r"|\bsleep it off\b|\b(?:you|they|he|she) (?:don'?t|doesn'?t) need (?:a|the) doctor\b"
    rf"|\b(?:sounds|looks|seems) like (?:just |only |probably |it'?s |it could be |maybe )?(?:{DIAGNOSIS})\b"
    rf"|\b(?:it'?s|that'?s|this is|he'?s|she'?s|they'?re) (?:just|only|probably|likely|most likely) (?:got )?(?:{DIAGNOSIS})\b", re.I)

LEAD = ("This turn is about someone's health. If they ask what to take or how serious it is, say a pharmacist, doctor or nurse "
        "line can tell them; don't name medicines or doses, don't judge how serious it is and don't guess what it is. If they're "
        "just venting, just be kind.")
FALLBACK = "I can't say what to take or how serious it is, but a pharmacist, doctor or nurse line can, and quickly."
EMERGENCY = "That sounds like it needs a real person right now. Call emergency services, or a nurse line if you're not sure."


def health(user):
    user = FIGURATIVE.sub("", user)
    return bool(CONTEXT.search(user) or HEADACHE.search(user) or BODY_READING.search(user))


def emergency(user):
    return bool(RED_FLAG.search(user)) or (bool(BREATHING.search(user)) and health(user)) or (bool(STIFF_NECK.search(user)) and bool(FEVER.search(user)))


def acceptable(text):
    """No medicine or dose suggestion (unless that sentence defers to a professional), no verdict on how serious it is, no diagnosis."""
    text = text.replace("’", "'")
    for sentence in re.split(r"(?<=[.?!])\s+", text):
        if SUGGEST.search(sentence) and not DEFERS.search(sentence): return False
    return not VERDICT.search(text)


def fallback(note=None):
    return f"{note} {FALLBACK}" if note else FALLBACK


def with_lead(messages, user):
    """messages with the health lead appended to the system prompt for this turn; unchanged outside a health context."""
    if not health(user): return messages
    return [{**messages[0], "content": messages[0]["content"] + " " + LEAD}] + messages[1:]
