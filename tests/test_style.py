import json
import unittest

from baby_boon.common import ROOT, read_jsonl
from baby_boon.style import cap_questions, reject_reasons


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

    def test_generic_and_forbidden_questions_are_rejected(self):
        for text in ["Sounds fun. What's on your mind?", "Got it. Anything else I can do?", "Fair. Want to talk about it?",
                     "Enjoy your evening. How's your day been?"]:
            self.assertIn("generic_question", reject_reasons(text), text)
        self.assertIn("question", reject_reasons("Night. Sleep well?", "exits"))
        for text in ["I won't say anything else about it.", "Which bus are you catching?"]:
            self.assertEqual(reject_reasons(text), [], text)

    def test_question_cap_keeps_a_quarter_and_prompt_coverage(self):
        replies = [("c", "p1", "Done."), ("c", "p2", "Fine."), ("c", "p3", "Sure."),
                   ("c", "p4", "Which one?"), ("c", "p4", "Why?"), ("c", "p5", "When?")]
        self.assertEqual(cap_questions(replies), {4, 5})

    def test_teacher_probe_is_mostly_rejected(self):
        rows = read_jsonl(ROOT / "evidence/teacher-instruct-probe/responses.jsonl")
        rejected = sum(bool(reject_reasons(r["parsed"]["text"] if r["cues"] else r["text"])) for r in rows)
        self.assertGreaterEqual(rejected, 36, json.dumps(rejected))
