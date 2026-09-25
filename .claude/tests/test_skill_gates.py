import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


HOOKS_DIR = Path(__file__).parents[1] / "hooks"


def load_module(name, filename):
    script = HOOKS_DIR / filename
    spec = importlib.util.spec_from_file_location(name, script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SkillGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp_home = tempfile.TemporaryDirectory()
        self.marker_root = Path(self.tmp_home.name) / "skill-markers"

        self.recorder = load_module("record_skill_invocation", "record-skill-invocation.py")
        self.coding_gate = load_module("require_coding_skill", "require-coding-skill.py")
        self.git_gate = load_module("require_git_skill", "require-git-skill.py")
        for module in (self.recorder, self.coding_gate, self.git_gate):
            module.MARKER_ROOT = self.marker_root

        self.tmp_repo = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp_home.cleanup()
        self.tmp_repo.cleanup()

    def run_module(self, module, payload):
        output = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(payload))), redirect_stdout(output):
            self.assertEqual(0, module.main())
        rendered = output.getvalue().strip()
        return json.loads(rendered) if rendered else None

    def assert_denied(self, result):
        self.assertIsNotNone(result)
        self.assertEqual("deny", result["hookSpecificOutput"]["permissionDecision"])
        return result["hookSpecificOutput"]["permissionDecisionReason"]

    def assert_allowed(self, result):
        self.assertIsNone(result)

    def write_marker(self, session_id, agent_id, skill):
        marker_dir = self.marker_root / session_id / agent_id
        marker_dir.mkdir(parents=True, exist_ok=True)
        (marker_dir / skill).touch()

    def missing_transcript_path(self):
        return str(Path(self.tmp_home.name) / "does-not-exist.jsonl")

    def edit_payload(self, session_id, agent_id, file_path):
        payload = {
            "session_id": session_id,
            "tool_name": "Edit",
            "tool_input": {"file_path": file_path, "old_string": "a", "new_string": "b"},
            "transcript_path": self.missing_transcript_path(),
        }
        if agent_id is not None:
            payload["agent_id"] = agent_id
        return payload

    # 1. Subagent invoked coding: marker under its own agent_id -> allowed.
    def test_subagent_marker_allows_matching_agent_edit(self):
        self.write_marker("sess-1", "agent-a", "coding")
        target = Path(self.tmp_repo.name) / "file.py"
        target.write_text("x = 1\n")
        result = self.run_module(
            self.coding_gate, self.edit_payload("sess-1", "agent-a", str(target))
        )
        self.assert_allowed(result)

    # 2. Marker only under main; a different subagent's edit is denied.
    def test_main_marker_does_not_cover_subagent(self):
        self.write_marker("sess-2", "main", "coding")
        target = Path(self.tmp_repo.name) / "file.py"
        target.write_text("x = 1\n")
        result = self.run_module(
            self.coding_gate, self.edit_payload("sess-2", "agent-b", str(target))
        )
        self.assert_denied(result)

    # 3. A typed /coding slash command records a main-thread marker that
    # then allows a main-thread edit.
    def test_typed_slash_command_records_marker_for_main_thread(self):
        expansion_payload = {
            "session_id": "sess-3",
            "hook_event_name": "UserPromptExpansion",
            "command_name": "coding",
        }
        self.run_module(self.recorder, expansion_payload)

        target = Path(self.tmp_repo.name) / "file.py"
        target.write_text("x = 1\n")
        result = self.run_module(
            self.coding_gate, self.edit_payload("sess-3", None, str(target))
        )
        self.assert_allowed(result)

    # 4. No marker anywhere and no usable transcript -> denied with an
    # actionable message naming the skill.
    def test_no_evidence_denies_with_actionable_message(self):
        target = Path(self.tmp_repo.name) / "file.py"
        target.write_text("x = 1\n")
        result = self.run_module(
            self.coding_gate, self.edit_payload("sess-4", None, str(target))
        )
        reason = self.assert_denied(result)
        self.assertIn("coding", reason)
        self.assertIn("Skill tool", reason)

    # 5. `git -C x commit -m y` via Bash on a feature branch, no git marker.
    def test_git_dash_c_commit_is_denied(self):
        payload = {
            "session_id": "sess-5",
            "agent_id": "agent-c",
            "tool_name": "Bash",
            "tool_input": {"command": "git -C /tmp/repo commit -m y"},
            "transcript_path": self.missing_transcript_path(),
        }
        result = self.run_module(self.git_gate, payload)
        self.assert_denied(result)

    # 6. Other newly-gated git mutations are each denied without a marker.
    def test_other_git_mutations_are_denied(self):
        commands = [
            "git switch -c b",
            "git pull",
            "git restore f",
            "git clean -fd",
        ]
        for command in commands:
            with self.subTest(command=command):
                payload = {
                    "session_id": "sess-6",
                    "agent_id": "agent-d",
                    "tool_name": "Bash",
                    "tool_input": {"command": command},
                    "transcript_path": self.missing_transcript_path(),
                }
                result = self.run_module(self.git_gate, payload)
                self.assert_denied(result)

    # 7. Extensionless file with a shebang first line is gated as source.
    def test_shebang_extensionless_file_is_denied(self):
        target = Path(self.tmp_repo.name) / "run-me"
        target.write_text("#!/usr/bin/env python3\nprint('hi')\n")
        result = self.run_module(
            self.coding_gate, self.edit_payload("sess-7", "agent-e", str(target))
        )
        self.assert_denied(result)

    # 8. A markdown edit is not gated by the coding skill.
    def test_markdown_edit_is_not_denied(self):
        target = Path(self.tmp_repo.name) / "notes.md"
        target.write_text("# notes\n")
        result = self.run_module(
            self.coding_gate, self.edit_payload("sess-8", "agent-f", str(target))
        )
        self.assert_allowed(result)


if __name__ == "__main__":
    unittest.main()
