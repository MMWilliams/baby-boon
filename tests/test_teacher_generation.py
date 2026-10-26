import tempfile
import unittest
from pathlib import Path

from scripts.generate_teacher import lock_run


class GenerationProvenance(unittest.TestCase):
    def test_identical_resume_and_changed_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            config = {"generator_sha256": "original", "prompt_ids": ["ex01", "ex02"]}
            lock_run(out, config)
            before = (out / "run.json").read_bytes()
            (out / "raw.jsonl").write_text("retained journal\n", encoding="utf-8")
            lock_run(out, dict(config))
            for changed in ({**config, "generator_sha256": "edited"},
                            {**config, "prompt_ids": ["ex01"]}):
                with self.assertRaisesRegex(ValueError, "inputs changed"):
                    lock_run(out, changed)
            self.assertEqual((out / "run.json").read_bytes(), before)
            self.assertEqual((out / "raw.jsonl").read_text(), "retained journal\n")

    def test_legacy_journal_cannot_be_relabelled_with_new_provenance(self):
        for name in ("raw.jsonl", "labels.jsonl"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                out = Path(temp)
                (out / name).write_text("{}\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "no run provenance"):
                    lock_run(out, {"generator_sha256": "new"})
                self.assertFalse((out / "run.json").exists())
