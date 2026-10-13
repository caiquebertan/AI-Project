"""check_schema_examples: the repo contract passes; the subset validator catches what it claims to."""
import json
import tempfile
import unittest
from pathlib import Path

from _util import run_script
import check_schema_examples as cse


class SchemaExamples(unittest.TestCase):
    def test_repo_contract_passes(self):
        res = run_script("check_schema_examples.py")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_validator_rejections(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "defs.schema.json").write_text(json.dumps(
                {"$defs": {"id": {"type": "string", "pattern": "^[a-f]{2}$"}}}))
            schema = {"type": "object", "additionalProperties": False, "required": ["id", "n"],
                      "properties": {"id": {"$ref": "defs.schema.json#/$defs/id"},
                                     "n": {"type": "integer", "minimum": 1},
                                     "tags": {"type": "array", "uniqueItems": True, "items": {"enum": ["x", "y"]}}}}
            s = cse.Schemas(base)
            ok = cse.validate({"id": "ab", "n": 1, "tags": ["x"]}, schema, s, "t")
            self.assertEqual(ok, [])
            errs = " | ".join(cse.validate({"id": "zz", "n": True, "tags": ["x", "x", "q"], "extra": 1}, schema, s, "t"))
            for needle in ("does not match", "expected integer", "not unique", "not in enum", "unexpected field"):
                self.assertIn(needle, errs)
            self.assertIn("missing 'n'", " ".join(cse.validate({"id": "ab"}, schema, s, "t")))

    def test_unsupported_keyword_and_constants(self):
        self.assertTrue(cse.unsupported_keywords({"properties": {"a": {"oneOf": []}}}))
        table = "| `TEXT_MAX_BYTES` | `4096` | x |\n| Name | Value | Used |"
        self.assertEqual(cse.protocol_constants(table), {"TEXT_MAX_BYTES": 4096})


if __name__ == "__main__":
    unittest.main()
