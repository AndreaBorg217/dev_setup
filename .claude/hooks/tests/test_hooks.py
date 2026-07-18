#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest import mock


HOOKS_DIR = Path(__file__).resolve().parent.parent
SETTINGS_PATH = HOOKS_DIR.parent / "settings.json"


def load_hook(filename: str) -> ModuleType:
    path = HOOKS_DIR / filename
    module_name = filename.removesuffix(".py").replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


policy = load_hook("policy.py")


def run_hook(
    script: str,
    tool_name: str,
    tool_input: dict[str, Any],
    hook_event_name: str = "PreToolUse",
) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(HOOKS_DIR / script)],
        check=False,
        capture_output=True,
        text=True,
        input=json.dumps({
            "hook_event_name": hook_event_name,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "session_id": "test-session",
            "cwd": str(Path.cwd()),
            "permission_mode": "default",
        }),
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout) if result.stdout.strip() else {}


class DerivedHookBehaviorTests(unittest.TestCase):
    def test_blocks_dangerous_shell_commands_without_blocking_scoped_cleanup(self) -> None:
        self.assertTrue(policy.check_dangerous_command("rm -rf ~/")["blocked"])
        self.assertFalse(policy.check_dangerous_command("rm -rf ./node_modules")["blocked"])

    def test_honors_safety_levels(self) -> None:
        command = "sudo rm /tmp/example"
        self.assertFalse(policy.check_dangerous_command(command, "high")["blocked"])
        self.assertTrue(policy.check_dangerous_command(command, "strict")["blocked"])

    def test_blocks_local_destructive_operations(self) -> None:
        commands = (
            "git push origin --delete obsolete",
            "psql -c 'DROP TABLE users'",
            "docker compose down",
            "kubectl delete namespace production",
            "argocd app sync example --prune",
            "terraform destroy",
            "aws s3 rb s3://example",
            "airflow tasks clear example_dag",
        )
        for command in commands:
            with self.subTest(command=command):
                self.assertTrue(policy.check_dangerous_command(command)["blocked"])

    def test_protects_main_and_destructive_hosting_cli_operations(self) -> None:
        self.assertTrue(policy.check_git_command("git commit -m fix", "main")["blocked"])
        self.assertTrue(policy.check_git_command("gh pr merge 42", "feature")["blocked"])
        destructive_glab_commands = (
            "glab mr merge 42",
            "glab mr accept 42",
            "glab mr delete 42",
            "glab issue close 42",
            "glab issue del 42",
            "glab release delete v1.0.0 --with-tag",
            "glab repo delete group/project --yes",
            "glab ci delete 123",
            "glab pipeline cancel pipeline 123",
            "glab variable remove API_TOKEN",
            "glab deploy-key delete 123",
            "glab runner delete 123 --force",
            "glab securefile rm 123",
            "glab container-registry repository del 123",
            "glab api projects/1 -X DELETE",
        )
        for command in destructive_glab_commands:
            with self.subTest(command=command):
                self.assertTrue(policy.check_git_command(command, "feature")["blocked"])

        self.assertFalse(policy.check_git_command("git status", "main")["blocked"])
        self.assertFalse(policy.check_git_command("glab mr view 42", "feature")["blocked"])
        self.assertFalse(policy.check_git_command("glab ci cancel pipeline 123 --dry-run", "feature")["blocked"])

    def test_protects_secrets_while_allowing_templates(self) -> None:
        self.assertTrue(policy.check_secrets("Read", {"file_path": ".env"})["blocked"])
        self.assertFalse(policy.check_secrets("Read", {"file_path": ".env.example"})["blocked"])
        self.assertTrue(policy.check_secrets("Bash", {"command": "cat credentials.json"})["blocked"])

    def test_blocks_test_deletion_without_blocking_test_execution(self) -> None:
        self.assertTrue(policy.check_tests_tool("Bash", {"command": "rm tests/unit.test.js"})["blocked"])
        self.assertFalse(policy.check_tests_tool("Bash", {"command": "npm test"})["blocked"])

    def test_blocks_new_skip_marker_but_allows_existing_one(self) -> None:
        new_skip = {
            "file_path": "tests/test_unit.py",
            "old_string": "def test_unit():",
            "new_string": "@pytest.mark.skip\ndef test_unit():",
        }
        existing_skip = {
            **new_skip,
            "old_string": "@pytest.mark.skip\ndef test_unit():",
        }
        self.assertTrue(policy.check_tests_tool("Edit", new_skip)["blocked"])
        self.assertFalse(policy.check_tests_tool("Edit", existing_skip)["blocked"])


class LocalCompositionTests(unittest.TestCase):
    def test_retains_infrastructure_specific_protection(self) -> None:
        denied = run_hook(
            "policy.py",
            "Bash",
            {"command": "terraform destroy"},
        )
        self.assertEqual(denied.get("hookSpecificOutput", {}).get("permissionDecision"), "deny")

    def test_cli_contract_denies_and_allows(self) -> None:
        denied = run_hook("policy.py", "Bash", {"command": "git reset --hard"})
        allowed = run_hook("policy.py", "Bash", {"command": "git status"})
        self.assertEqual(denied.get("hookSpecificOutput", {}).get("permissionDecision"), "deny")
        self.assertEqual(allowed, {})

    def test_every_registered_hook_script_exists(self) -> None:
        settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        commands = [
            hook["command"]
            for group in settings["hooks"]["PreToolUse"]
            for hook in group["hooks"]
        ]

        for command in commands:
            marker = "~/.claude/hooks/"
            if marker in command:
                filename = command.split(marker, maxsplit=1)[1].split(maxsplit=1)[0]
                self.assertTrue((HOOKS_DIR / filename).exists(), command)

        self.assertIn("python3 ~/.claude/hooks/policy.py", commands)
        self.assertNotIn("rtk hook claude", commands)
        self.assertFalse(any("block-dangerous-commands.py" in command for command in commands))
        self.assertFalse(any("git-safety.py" in command for command in commands))
        self.assertFalse(any("protect-secrets.py" in command for command in commands))
        self.assertFalse(any("protect-tests.py" in command for command in commands))
        self.assertFalse(any("filter-noisy-output" in command for command in commands))
        self.assertFalse(any("block-destructive-operations" in command for command in commands))
        self.assertFalse(any(command.startswith("node ") for command in commands))

class ConsolidatedPolicyTests(unittest.TestCase):
    def assert_denied(self, command: str, rule_id: str | None = None) -> None:
        output = run_hook("policy.py", "Bash", {"command": command})
        specific = output.get("hookSpecificOutput", {})
        self.assertEqual(specific.get("permissionDecision"), "deny", command)
        if rule_id:
            self.assertIn(f"[{rule_id}]", specific.get("permissionDecisionReason", ""), command)

    def test_blocks_adversarial_destructive_command_forms(self) -> None:
        cases = (
            ("'rm' -rf ~", "rm-home"),
            ("x=rm; $x -rf ~", "rm-home"),
            ("git -C /tmp/repo reset --hard", "git-reset-hard"),
            ("find . -type f -delete", "find-delete"),
            ("rsync -a --delete empty/ target/", "rsync-delete"),
            ("diskutil eraseDisk APFS Empty /dev/disk2", "diskutil-erase"),
            ("gcloud projects delete production", "gcloud-delete"),
            ("redis-cli FLUSHALL", "redis-flush"),
            ("gh api repos/example/project -X DELETE", "gh-api-delete"),
        )
        for command, rule_id in cases:
            with self.subTest(command=command):
                self.assert_denied(command, rule_id)

    def test_blocks_secret_allowlist_smuggling_and_indirect_readers(self) -> None:
        cases = (
            "cat ~/.aws/credentials .env.example",
            "sed -n '1,20p' .env",
            "'sed' -n '1,20p' .env",
            "x=sed; $x -n '1,20p' .env",
            "rg TOKEN .env",
            "python3 -c 'print(open(\".env\").read())'",
            "git add .env",
        )
        for command in cases:
            with self.subTest(command=command):
                self.assert_denied(command)

    def test_blocks_sensitive_file_symlink_alias(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            secret = Path(directory) / ".env"
            alias = Path(directory) / "safe-looking.txt"
            secret.write_text("TOKEN=secret\n", encoding="utf-8")
            alias.symlink_to(secret)
            output = run_hook("policy.py", "Read", {"file_path": str(alias)})
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("[env-file]", output["hookSpecificOutput"]["permissionDecisionReason"])

    def test_blocks_test_directory_deletion_variants(self) -> None:
        for command in ("rm -rf tests", "rm -rf src/test", "find tests -type f -delete"):
            with self.subTest(command=command):
                self.assert_denied(command, "delete-test")

    def test_blocks_test_overwrite_and_assertion_weakening(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            test_file = Path(directory) / "test_policy.py"
            test_file.write_text("def test_policy():\n    assert value\n", encoding="utf-8")
            overwritten = run_hook(
                "policy.py",
                "Write",
                {"file_path": str(test_file), "content": "def test_policy():\n    assert True\n"},
            )
            weakened = run_hook(
                "policy.py",
                "Edit",
                {
                    "file_path": str(test_file),
                    "old_string": "assert value",
                    "new_string": "value",
                },
            )
        self.assertEqual(overwritten["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(weakened["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_locks_configuration_edits_and_hot_reload(self) -> None:
        edit = run_hook(
            "policy.py",
            "Edit",
            {"file_path": str(HOOKS_DIR / "policy.py"), "old_string": "a", "new_string": "b"},
        )
        change = run_hook("policy.py", "", {}, hook_event_name="ConfigChange")
        self.assertEqual(edit["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(change.get("decision"), "block")

    def test_blocks_bash_access_to_protected_configuration(self) -> None:
        commands = (
            "cat ~/.claude/hooks/policy.py",
            "python3 -c 'open(\".claude/hooks/policy.py\", \"w\").write(\"\")'",
            "git checkout -- .claude/settings.json",
        )
        for command in commands:
            with self.subTest(command=command):
                self.assert_denied(command, "config-locked")

    def test_caps_large_text_reads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            large_file = Path(directory) / "large.log"
            large_file.write_text("line with useful data\n" * 8_000, encoding="utf-8")
            output = run_hook("policy.py", "Read", {"file_path": str(large_file)})
        specific = output["hookSpecificOutput"]
        self.assertEqual(specific["permissionDecision"], "allow")
        self.assertEqual(specific["updatedInput"]["limit"], policy.MAX_READ_LINES)

    def test_rewrites_supported_commands_and_preserves_input(self) -> None:
        cases = (
            ("mvn clean verify", "rtk mvn clean verify"),
            ("git status", "rtk git status"),
        )
        for command, expected in cases:
            with self.subTest(command=command):
                output = run_hook(
                    "policy.py",
                    "Bash",
                    {"command": command, "description": "probe", "timeout": 120_000},
                )
                updated = output["hookSpecificOutput"]["updatedInput"]
                self.assertEqual(updated["command"], expected)
                self.assertEqual(updated["description"], "probe")
                self.assertEqual(updated["timeout"], 120_000)

    def test_passes_through_unsupported_and_disabled_commands(self) -> None:
        self.assertEqual(run_hook("policy.py", "Bash", {"command": "echo hello"}), {})
        self.assertEqual(
            run_hook("policy.py", "Bash", {"command": "RTK_DISABLED=1 mvn clean verify"}),
            {},
        )

    def test_passes_through_nested_maven_command(self) -> None:
        self.assertEqual(run_hook("policy.py", "Bash", {"command": 'bash -lc "mvn clean verify"'}), {})

    def test_passes_through_when_rtk_fails(self) -> None:
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "mvn clean verify"},
            "cwd": str(Path.cwd()),
        }
        with mock.patch.object(policy, "_run_rtk", side_effect=OSError("rtk unavailable")):
            output = policy.evaluate_pre_tool(payload)
        self.assertEqual(output, {})

    def test_malformed_input_fails_closed(self) -> None:
        result = subprocess.run(
            [sys.executable, str(HOOKS_DIR / "policy.py")],
            check=False,
            capture_output=True,
            text=True,
            input="{not-json",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("failed closed", result.stderr)

    def test_web_tool_interception_prompts(self) -> None:
        for tool in ("WebSearch", "WebFetch"):
            with self.subTest(tool=tool):
                output = run_hook("policy.py", tool, {"query": "test"})
                specific = output.get("hookSpecificOutput", {})
                self.assertEqual(specific.get("permissionDecision"), "ask")
                self.assertIn("Haiku", specific.get("permissionDecisionReason", ""))


if __name__ == "__main__":
    unittest.main()
