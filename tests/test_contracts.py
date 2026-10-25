import unittest

from baby_boon.cues import parse_response
from baby_boon.training_data import encode_example, pad_batch


class ToyTokenizer:
    eos_token_id = 9
    def apply_chat_template(self, *args, **kwargs): return [1,2,3]
    def encode(self, *args, **kwargs): return [7,8]


class Contracts(unittest.TestCase):
    def test_assistant_boundary_and_eos(self):
        row = encode_example(ToyTokenizer(), {"id":"test","messages":[],"system":"s","target":"answer"})
        self.assertEqual(row["input_ids"], [1,2,3,7,8,9])
        self.assertEqual(row["labels"], [-100,-100,-100,7,8,9])
        # Causal shifting supervises 7 from the final prompt position and EOS from 8.
        self.assertEqual(row["labels"][1:], [-100,-100,7,8,9])

    def test_no_silent_truncation(self):
        with self.assertRaises(ValueError):
            encode_example(ToyTokenizer(), {"messages":[],"system":"s","target":"a"}, max_length=5)

    def test_padding_is_never_a_target(self):
        rows = [{"input_ids":[1,2,9],"labels":[-100,2,9],"attention_mask":[1,1,1]},
                {"input_ids":[1,9],"labels":[-100,9],"attention_mask":[1,1]}]
        batch = pad_batch(rows,9)
        self.assertEqual(batch["labels"].tolist(),[[-100,2,9],[-100,9,-100]])
        self.assertEqual(batch["attention_mask"].tolist(),[[1,1,1],[1,1,0]])

    def test_cue_contract(self):
        parsed = parse_response("Nice work.\n<cue>warm|smile|1")
        self.assertEqual(parsed,{"text":"Nice work.","tone":"warm","expression":"smile","intensity":1,"cue_valid":True})

    def test_invalid_cues_fall_back_without_actuation(self):
        for suffix in ["move|hug|1","warm|smile|3","warm|smile|-1","warm|smile|0.5","warm|smile|1\nextra", "warm|smile|1<cue>calm|neutral|0"]:
            result = parse_response("hello\n<cue>"+suffix)
            self.assertFalse(result["cue_valid"])
            self.assertEqual(result["text"],"hello")
            self.assertEqual(result["intensity"],0)
        self.assertFalse(parse_response("hello")["cue_valid"])
        self.assertEqual(parse_response("hello <cue tone=0>")["text"], "hello")
        self.assertFalse(parse_response("hello <cue tone=0>")["cue_valid"])
        self.assertEqual(parse_response("hello <concern>0")["text"], "hello")
        self.assertFalse(parse_response("<cue>warm|smile|1")["cue_valid"])


if __name__ == "__main__": unittest.main()
