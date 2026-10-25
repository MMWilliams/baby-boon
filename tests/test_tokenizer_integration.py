import unittest

from transformers import AutoTokenizer
from tinysocial.common import source
from tinysocial.training_data import encode_example


class TokenizerIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B", revision=source("Qwen/Qwen3-0.6B")["revision"], local_files_only=True)

    def test_real_chat_template_and_mask(self):
        row = {"id":"mask-integration","system":"You are a conversational AI.",
               "messages":[{"role":"user","content":"USER_ONLY_SECRET_197"}],"target":"Hello.\n<cue>warm|smile|1"}
        encoded = encode_example(self.tokenizer,row)
        supervised = [v for v in encoded["labels"] if v != -100]
        self.assertEqual(self.tokenizer.decode(supervised),"Hello.\n<cue>warm|smile|1<|im_end|>")
        n = encoded["labels"].index(supervised[0])
        prefix = self.tokenizer.decode(encoded["input_ids"][:n])
        self.assertIn("USER_ONLY_SECRET_197",prefix)
        self.assertTrue(prefix.endswith("<|im_start|>assistant\n<think>\n\n</think>\n\n"))
        self.assertEqual(encoded["labels"][:n],[-100]*n)


if __name__=="__main__": unittest.main()
