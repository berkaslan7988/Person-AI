"""Prompt checks in separate processes with disposable data directories."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROMPT_SCRIPT = """
import json
import os
from pathlib import Path
import sys
import server

path = Path(os.environ['PAI_DATA_DIR']) / 'system_prompt.txt'
outputs = []
for content in json.load(sys.stdin):
    if path.exists():
        path.unlink()
    if content is not None:
        path.write_bytes(bytes(content))
    outputs.append(server.system_instruction(
        {'name': 'Sample character', 'traits': 'curious and patient'}, {}))
print(json.dumps({'rules': server.DEFAULT_RULES, 'outputs': outputs}))
server.db.conn.close()
"""


class PromptTests(unittest.TestCase):
    def prompts(self, *contents):
        with tempfile.TemporaryDirectory(prefix="pai-prompt-tests-") as data:
            # Prevent any first-run migration of the user's legacy database.
            (Path(data) / "person_ai.db").touch()
            env = dict(os.environ, PAI_DATA_DIR=data, PAI_FAKE="1",
                       PAI_PUBLIC_HOST="", PAI_ACCESS_TEAM="", PAI_ACCESS_AUD="")
            result = subprocess.run(
                [sys.executable, "-c", PROMPT_SCRIPT], cwd=ROOT, env=env,
                input=json.dumps([list(c) if c is not None else None for c in contents]),
                capture_output=True, text=True, encoding="utf-8", timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)

    def test_default_without_override(self):
        result = self.prompts(None)
        prompt = result["outputs"][0]
        self.assertIn(result["rules"], prompt)
        for word in ("uncensored", "NSFW", "safety protocols"):
            self.assertNotIn(word.casefold(), prompt.casefold())

    def test_local_override_and_reload(self):
        first = "Local rules: keep the lantern lit."
        second = "Updated rules: follow the river.\n"
        result = self.prompts(first.encode("utf-8"), second.encode("utf-8"))
        for prompt, rules in zip(result["outputs"], (first + "\n", second)):
            self.assertTrue(prompt.endswith(rules))
            self.assertNotIn(result["rules"], prompt)

    def test_blank_override_uses_default(self):
        result = self.prompts(b"", b" \t\n")
        for prompt in result["outputs"]:
            self.assertTrue(prompt.endswith(result["rules"]))

    def test_invalid_utf8_uses_default(self):
        result = self.prompts(b"\xff")
        self.assertTrue(result["outputs"][0].endswith(result["rules"]))


if __name__ == "__main__":
    unittest.main()
