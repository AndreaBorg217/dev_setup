import importlib.util
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "hooks" / "advise-agent-routing.py"
SPEC = importlib.util.spec_from_file_location("agent_routing", SCRIPT)
routing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(routing)


class AgentRoutingTests(unittest.TestCase):
    def run_hook(self, tool_name, tool_input):
        output = io.StringIO()
        payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
        with patch("sys.stdin", io.StringIO(payload)), redirect_stdout(output):
            self.assertEqual(0, routing.main())
        rendered = output.getvalue().strip()
        return json.loads(rendered) if rendered else None

    def assert_denied(self, tool_input):
        result = self.run_hook("Agent", tool_input)
        self.assertEqual(
            "deny", result["hookSpecificOutput"]["permissionDecision"]
        )

    def assert_asks(self, tool_input):
        result = self.run_hook("Agent", tool_input)
        self.assertEqual(
            "ask", result["hookSpecificOutput"]["permissionDecision"]
        )

    def test_known_agents_accept_matching_model(self):
        for agent_type, model in routing.LOCAL_AGENT_MODELS.items():
            with self.subTest(agent_type=agent_type, model=model):
                self.assertIsNone(
                    self.run_hook(
                        "Agent", {"subagent_type": agent_type, "model": model}
                    )
                )

    def test_known_agents_reject_incompatible_model_for_both_type_fields(self):
        self.assert_denied({"subagent_type": "explorer", "model": "sonnet"})
        result = self.run_hook(
            "Task", {"type": "builder", "model": "claude-haiku-4-5"}
        )
        self.assertEqual(
            "deny", result["hookSpecificOutput"]["permissionDecision"]
        )

    def test_every_agent_type_requires_approval_for_opus(self):
        for agent_type in ("analyst", "plugin:reviewer", "general-purpose", ""):
            with self.subTest(agent_type=agent_type):
                self.assert_asks(
                    {"subagent_type": agent_type, "model": "claude-opus-5"}
                )

    def test_unknown_agents_accept_explicit_haiku_or_sonnet(self):
        for model in ("haiku", "claude-sonnet-5"):
            tool_input = {"subagent_type": "plugin:reviewer", "model": model}
            with self.subTest(model=model):
                self.assertIsNone(self.run_hook("Agent", tool_input))

    def test_omitted_model_is_denied_for_every_agent_type(self):
        for agent_type in ("explorer", "plugin:reviewer", "general-purpose", ""):
            with self.subTest(agent_type=agent_type):
                self.assert_denied({"subagent_type": agent_type})

    def test_explicit_unknown_model_is_denied(self):
        self.assert_denied(
            {"subagent_type": "plugin:reviewer", "model": "inherit"}
        )
        self.assert_denied(
            {"subagent_type": "plugin:reviewer", "model": "notsonnet"}
        )
        self.assert_denied(
            {"subagent_type": "plugin:reviewer", "model": "sonnet-opus"}
        )

    def test_non_agent_tool_is_silent(self):
        self.assertIsNone(self.run_hook("Read", {"file_path": "large.txt"}))


if __name__ == "__main__":
    unittest.main()
