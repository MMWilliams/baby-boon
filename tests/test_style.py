import json
import unittest

from baby_boon.common import ROOT, read_jsonl
from baby_boon.style import reject_reasons


class Style(unittest.TestCase):
    def test_known_teacher_defects_are_rejected(self):
        cases = {
            "That's lovely. 🍅": "emoji",
            "Ain't no need to explain, man. Just let it sit.": "slang",
            "Okay, I'm all quiet. I'm right here with you.": "inner_life",
            "Oh, I'd love to hear it.": "stock_opener",
            "Sure, I'll hold the door for you.": "physical_action",
            "That's *so* sweet.": "markup",
            "One. Two. Three. Four.": "too_long",
        }
        for text, reason in cases.items():
            self.assertIn(reason, reject_reasons(text), text)

    def test_plain_honest_replies_pass(self):
        for text in ["I can't pass you the cup; my arms are switched off. Is it within reach?",
                     "I see what you mean. One missed line rarely ruins a speech.",
                     "Fair enough. Something light, then: what's the best thing you ate this week?"]:
            self.assertEqual(reject_reasons(text), [], text)

    def test_teacher_probe_is_mostly_rejected(self):
        rows = read_jsonl(ROOT / "evidence/teacher-instruct-probe/responses.jsonl")
        rejected = sum(bool(reject_reasons(r["parsed"]["text"] if r["cues"] else r["text"])) for r in rows)
        self.assertGreaterEqual(rejected, 36, json.dumps(rejected))
