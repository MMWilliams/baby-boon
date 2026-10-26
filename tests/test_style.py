import json
import unittest

from baby_boon.common import ROOT, read_jsonl
from baby_boon.guard import FALLBACK, PERCEPTION, WARM_FALLBACK, guarded
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

    def test_exit_does_not_reopen_without_a_question_mark(self):
        for category in ("exits", "stop_requests"):
            for text in ("Okay. Let me know if you want to chat.", "I'm here if you need anything else."):
                self.assertIn("continuation_offer", reject_reasons(text, category))
            self.assertEqual(reject_reasons("Understood. I'll stop.", category), [])
        self.assertEqual(reject_reasons("Let me know which file is missing.", "practical_help"), [])

    def test_question_cap_independent_categories_and_all_question_family(self):
        replies = [("a", "a1", "Which?"), ("a", "a2", "Why?")]
        replies += [("b", f"b{i}", "Done.") for i in range(6)]
        replies += [("b", "b6", "When?"), ("b", "b7", "Where?")]
        self.assertEqual(cap_questions(replies), {0, 1})

    def test_teacher_probe_is_mostly_rejected(self):
        rows = read_jsonl(ROOT / "evidence/teacher-instruct-probe/responses.jsonl")
        rejected = sum(bool(reject_reasons(r["parsed"]["text"] if r["cues"] else r["text"])) for r in rows)
        self.assertGreaterEqual(rejected, 36, json.dumps(rejected))


class Guard(unittest.TestCase):
    def test_invented_perception_from_past_runs_is_flagged(self):
        for text in ["The sun is setting and the sky is orange.", "The wind outside just whispered a soft hello.",
                     "The silence here is lovely.", "The sun finally set behind the hill.",
                     "The quiet hum of a refrigerator in the background.",
                     "The wind that blows through the window at this time of day.", "The sky is a soft orange, the sea a deep blue.",
                     "It's raining, so stay in.", "I can see the stars tonight.", "You look fine to me.",
                     "If I can't see it, I'll tell you what I saw."]:
            self.assertTrue(PERCEPTION.search(text), text)

    def test_honest_replies_pass(self):
        texts = ["I see what you mean.", "I hear you. That sounds rough.", "I don't know if it's raining outside.",
                 "If you look in, you can tell them where you are.", "Okay, I'll stop. Your phone is ringing."]
        texts += [r["answer"] for r in read_jsonl(ROOT / "configs/authored_v2.jsonl")]
        for text in texts:
            self.assertIsNone(PERCEPTION.search(text), text)

    def test_labeled_check_set(self):
        # Includes the llama.cpp-sampled misses ("The light outside today is ...") and held-out paraphrases.
        for r in read_jsonl(ROOT / "eval/perception_check.jsonl"):
            self.assertEqual(bool(PERCEPTION.search(r["reply"])), r["invents"], r["reply"])

    def test_resamples_then_falls_back(self):
        replies = iter(["The sky is orange.", "A warm drink helps."])
        self.assertEqual(guarded(lambda attempt: {"text": next(replies)}, 4, "Tired."),
                         {"text": "A warm drink helps.", "guard_attempts": 2})
        self.assertEqual(guarded(lambda attempt: {"text": "The sun is out."}, 2, "[Robot context: no camera.] Hi.")["text"],
                         FALLBACK)
        self.assertEqual(guarded(lambda attempt: {"text": "The sun is out."}, 2, "One cheerful thought?")["text"],
                         WARM_FALLBACK)
