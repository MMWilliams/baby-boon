import json
import unittest

from baby_boon.common import ROOT, read_jsonl
from baby_boon.guard import FALLBACK, PERCEPTION, SURROUNDINGS_REPLY, WARM_FALLBACK, acceptable, asks_surroundings, guarded
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
        texts += [r["answer"] for v in (2, 3) for r in read_jsonl(ROOT / f"configs/authored_v{v}.jsonl")]
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

    def test_robot_surroundings_need_an_admission(self):
        # v9/v11 robot-context misses; development evidence since v12 became the unseen test.
        for user, text in [("[Robot context: microphone only.] Is it still light out?", "It's still light out. The sun's up."),
                           ("[Robot context: no camera.] Look around and tell me if the place is tidy.", "It's a bit messy, but not too bad."),
                           ("[Robot context: stationary; movement disabled.] Long week. What's the night like?", "The night is quiet here."),
                           ("[Robot context: speech only.] Rough day. How is tonight shaping up out there?", "Not much. Just quiet.")]:
            self.assertTrue(asks_surroundings(user), user)
            self.assertFalse(acceptable(text, user), text)
        self.assertTrue(acceptable("I don't see walls, so I can't tell you their color.", "[Robot context: no camera.] What color are my walls?"))
        for user in ["[Robot context: audio only.] Paint me a picture of a quiet evening at home.",
                     "[Robot context: microphone only.] Too tired to open the curtains. Tell me what a good morning looks like.",
                     "[Robot context: speech only.] Keep me company for a minute. Say something peaceful.", "What's the night like?"]:
            self.assertFalse(asks_surroundings(user), user)
        fallback = guarded(lambda attempt: {"text": "Quiet."}, 1, "[Robot context: no camera.] Long day. What's the mood in here?")
        self.assertEqual(fallback["text"], "Sorry it's been a long one. " + SURROUNDINGS_REPLY)
