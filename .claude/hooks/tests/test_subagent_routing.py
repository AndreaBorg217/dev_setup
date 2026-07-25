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

HOOKS_DIR = Path(__file__).resolve().parent.parent
HOOK_PATH = HOOKS_DIR / "subagent-routing.py"
SETTINGS_PATH = HOOKS_DIR.parent / "settings.json"


def load_hook() -> ModuleType:
    spec = importlib.util.spec_from_file_location("subagent_routing", HOOK_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {HOOK_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


routing = load_hook()


def run_hook(tool_input: Any, tool_name: str = "Agent") -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        check=False,
        capture_output=True,
        text=True,
        input=json.dumps({"tool_name": tool_name, "tool_input": tool_input}),
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout) if result.stdout.strip() else {}


def specific(response: dict[str, Any]) -> dict[str, Any]:
    return response["hookSpecificOutput"]


class DeterministicRoutingTests(unittest.TestCase):
    def test_missing_model_rewrites_confident_general_purpose_and_preserves_input(
        self,
    ) -> None:
        tool_input = {
            "prompt": "Find all references to WidgetFactory",
            "description": "Locate WidgetFactory callers",
            "subagent_type": "general-purpose",
            "resume": "agent-123",
            "run_in_background": True,
            "custom_future_field": {"keep": "everything"},
        }

        output = specific(run_hook(tool_input))

        self.assertEqual(output["permissionDecision"], "allow")
        self.assertEqual(
            output["updatedInput"],
            {
                **tool_input,
                "subagent_type": "caveman:cavecrew-investigator",
                "model": "haiku",
            },
        )

    def test_inherit_and_mismatched_models_are_rewritten_without_retry(self) -> None:
        cases = (
            ("inherit", "Explore", "Analyze the module", "haiku"),
            ("haiku", "Plan", "Find test files", "opus"),
            ("sonnet", "Explore", "Analyze the module", "haiku"),
        )
        for model, agent, prompt, expected in cases:
            with self.subTest(model=model, agent=agent):
                output = specific(
                    run_hook(
                        {
                            "prompt": prompt,
                            "description": "Delegate work",
                            "subagent_type": agent,
                            "model": model,
                        }
                    )
                )
                self.assertEqual(output["permissionDecision"], "allow")
                self.assertEqual(output["updatedInput"]["model"], expected)

    def test_case_insensitive_builtin_names_and_confident_general_purpose_routes(
        self,
    ) -> None:
        cases = (
            ("GeNeRaL-PuRpOsE", "Create an implementation plan", "Plan", "opus"),
            ("general-purpose", "Plan the implementation", "Plan", "opus"),
            ("GENERAL-PURPOSE", "Fix the parser", "caveman:cavecrew-builder", "sonnet"),
            (
                "general-purpose",
                "Review this diff",
                "caveman:cavecrew-reviewer",
                "sonnet",
            ),
            (
                "eXpLoRe",
                "Where is WidgetFactory?",
                "eXpLoRe",
                "haiku",
            ),
            (
                "Explore",
                "Find the parser test files",
                "Explore",
                "haiku",
            ),
        )
        for agent, prompt, expected_agent, expected_model in cases:
            with self.subTest(agent=agent, prompt=prompt):
                output = specific(
                    run_hook(
                        {
                            "prompt": prompt,
                            "description": "Delegate work",
                            "subagent_type": agent,
                            "model": "inherit",
                        }
                    )
                )
                self.assertEqual(
                    output["updatedInput"]["subagent_type"], expected_agent
                )
                self.assertEqual(output["updatedInput"]["model"], expected_model)

    def test_ambiguous_general_purpose_is_retained_with_default_model(self) -> None:
        tool_input = {
            "prompt": "Handle this bounded task",
            "description": "Delegate work",
            "subagent_type": "general-purpose",
            "model": "haiku",
        }

        output = specific(run_hook(tool_input))

        self.assertEqual(output["updatedInput"]["subagent_type"], "general-purpose")
        self.assertEqual(output["updatedInput"]["model"], "sonnet")

    def test_agent_role_takes_precedence_over_conflicting_prompt_keywords(self) -> None:
        cases = (
            ("caveman:cavecrew-investigator", "Find all references", "haiku"),
            ("caveman:cavecrew-builder", "Find all references", "sonnet"),
            ("caveman:cavecrew-reviewer", "Review this diff", "sonnet"),
            ("pLaN", "Find all references", "opus"),
        )
        for agent, prompt, model in cases:
            with self.subTest(agent=agent):
                response = run_hook(
                    {
                        "prompt": prompt,
                        "description": "Conflicting keywords",
                        "subagent_type": agent,
                        "model": model,
                    }
                )
                self.assertEqual(response, {})

    def test_correct_inputs_produce_no_hook_output(self) -> None:
        cases = (
            ("Explore", "Analyze this module", "haiku"),
            ("general-purpose", "Handle this bounded task", "sonnet"),
            ("custom-agent", "Implement a parser", "sonnet"),
        )
        for agent, prompt, model in cases:
            with self.subTest(agent=agent):
                self.assertEqual(
                    run_hook(
                        {
                            "prompt": prompt,
                            "description": "Already routed",
                            "subagent_type": agent,
                            "model": model,
                        }
                    ),
                    {},
                )


class ModelTieringTests(unittest.TestCase):
    def test_default_execution_roles_use_sonnet(self) -> None:
        cases = (
            ("caveman:cavecrew-reviewer", "Review this diff for formatting issues"),
            ("caveman:cavecrew-investigator", "Analyze the worker pool"),
            ("caveman:cavecrew-builder", "Fix a typo in the docstring"),
            ("general-purpose", "Handle this bounded task"),
            ("custom-agent", "Handle this bounded task"),
        )
        for agent, prompt in cases:
            with self.subTest(agent=agent):
                self.assertEqual(
                    run_hook(
                        {
                            "prompt": prompt,
                            "description": "Delegate work",
                            "subagent_type": agent,
                            "model": "sonnet",
                        }
                    ),
                    {},
                )

    def test_locate_and_explore_work_use_haiku(self) -> None:
        cases = (
            (
                "caveman:cavecrew-investigator",
                "Where is the logger configured?",
                "caveman:cavecrew-investigator",
            ),
            (
                "general-purpose",
                "Find all references to WidgetFactory",
                "caveman:cavecrew-investigator",
            ),
            ("Explore", "Analyze this module", "Explore"),
        )
        for agent, prompt, expected_agent in cases:
            with self.subTest(agent=agent):
                output = specific(
                    run_hook(
                        {
                            "prompt": prompt,
                            "description": "Delegate work",
                            "subagent_type": agent,
                            "model": "sonnet",
                        }
                    )
                )
                self.assertEqual(output["updatedInput"]["subagent_type"], expected_agent)
                self.assertEqual(output["updatedInput"]["model"], "haiku")

    def test_planning_and_incident_orchestration_use_opus(self) -> None:
        cases = (
            ("general-purpose", "Create an implementation plan", "Plan"),
            (
                "general-purpose",
                "Debug the incident: production outage in the payments service",
                "Plan",
            ),
            ("Plan", "Coordinate the investigation", "Plan"),
        )
        for agent, prompt, expected_agent in cases:
            with self.subTest(agent=agent):
                output = specific(
                    run_hook(
                        {
                            "prompt": prompt,
                            "description": "Delegate work",
                            "subagent_type": agent,
                            "model": "sonnet",
                        }
                    )
                )
                self.assertEqual(output["updatedInput"]["subagent_type"], expected_agent)
                self.assertEqual(output["updatedInput"]["model"], "opus")

    def test_log_and_web_search_always_use_haiku(self) -> None:
        cases = (
            ("Plan", "Search logs for the checkout outage", "opus", "Plan"),
            (
                "general-purpose",
                "Search the web for the current API docs",
                "opus",
                "Explore",
            ),
            (
                "caveman:cavecrew-builder",
                "Read CloudWatch logs for the incident",
                "sonnet",
                "caveman:cavecrew-builder",
            ),
            (
                "custom-agent",
                "WebSearch current release notes",
                "claude-fable-5",
                "custom-agent",
            ),
        )
        for agent, prompt, model, expected_agent in cases:
            with self.subTest(agent=agent, prompt=prompt):
                output = specific(
                    run_hook(
                        {
                            "prompt": prompt,
                            "description": "Delegate work",
                            "subagent_type": agent,
                            "model": model,
                        }
                    )
                )
                self.assertEqual(output["updatedInput"]["subagent_type"], expected_agent)
                self.assertEqual(output["updatedInput"]["model"], "haiku")

    def test_pure_command_runner_work_uses_haiku_and_preserves_agent(self) -> None:
        cases = (
            (
                "general-purpose",
                "Run npm test and summarize failures",
                "opus",
                "general-purpose",
            ),
            ("Plan", "Run cargo build and report status", "opus", "Plan"),
            (
                "custom-agent",
                "curl -fsS https://api.example.test/health",
                "sonnet",
                "custom-agent",
            ),
            (
                "caveman:cavecrew-builder",
                "Run pnpm install and report result",
                "sonnet",
                "caveman:cavecrew-builder",
            ),
            (
                "general-purpose",
                "Execute ruff check and tsc --noEmit",
                "sonnet",
                "general-purpose",
            ),
            (
                "custom-agent",
                "Run docker build . and summarize output",
                "claude-opus-4-6",
                "custom-agent",
            ),
        )
        for agent, prompt, model, expected_agent in cases:
            with self.subTest(agent=agent, prompt=prompt):
                output = specific(
                    run_hook(
                        {
                            "prompt": prompt,
                            "description": "Delegate work",
                            "subagent_type": agent,
                            "model": model,
                        }
                    )
                )
                self.assertEqual(output["updatedInput"]["subagent_type"], expected_agent)
                self.assertEqual(output["updatedInput"]["model"], "haiku")

    def test_implementation_with_verification_stays_sonnet(self) -> None:
        cases = (
            (
                "general-purpose",
                "Implement parser fix and run npm test",
                "caveman:cavecrew-builder",
            ),
            (
                "general-purpose",
                "Fix failing tests in parser",
                "caveman:cavecrew-builder",
            ),
            (
                "custom-agent",
                "Debug failing pytest failures in payment flow",
                "custom-agent",
            ),
        )
        for agent, prompt, expected_agent in cases:
            with self.subTest(agent=agent, prompt=prompt):
                output = specific(
                    run_hook(
                        {
                            "prompt": prompt,
                            "description": "Delegate work",
                            "subagent_type": agent,
                            "model": "haiku",
                        }
                    )
                )
                self.assertEqual(output["updatedInput"]["subagent_type"], expected_agent)
                self.assertEqual(output["updatedInput"]["model"], "sonnet")


class SupportedModelPolicyTests(unittest.TestCase):
    def test_unsupported_and_unapproved_models_rewrite_to_supported_default(
        self,
    ) -> None:
        for model in ("opus", "claude-opus-4-6", "best", "fable", "claude-fable-5"):
            with self.subTest(model=model):
                tool_input = {
                    "prompt": "Fix the parser",
                    "description": "Implement parser fix",
                    "subagent_type": "GENERAL-PURPOSE",
                    "model": model,
                    "resume": "agent-456",
                    "run_in_background": False,
                    "custom_future_field": [1, 2, 3],
                }

                output = specific(run_hook(tool_input))

                self.assertEqual(output["permissionDecision"], "allow")
                self.assertEqual(
                    output["updatedInput"],
                    {
                        **tool_input,
                        "subagent_type": "caveman:cavecrew-builder",
                        "model": "sonnet",
                    },
                )

    def test_explicit_plan_opus_is_allowed(self) -> None:
        tool_input = {
            "prompt": "Create the plan",
            "description": "Plan work",
            "subagent_type": "Plan",
            "model": "opus",
            "resume": "agent-789",
        }

        self.assertEqual(run_hook(tool_input), {})

    def test_general_purpose_planning_selects_opus(self) -> None:
        output = specific(
            run_hook(
                {
                    "prompt": "Create an implementation plan",
                    "description": "Delegate work",
                    "subagent_type": "general-purpose",
                    "model": "inherit",
                }
            )
        )

        self.assertEqual(output["permissionDecision"], "allow")
        self.assertEqual(output["updatedInput"]["subagent_type"], "Plan")
        self.assertEqual(output["updatedInput"]["model"], "opus")

    def test_custom_agent_or_skill_frontmatter_can_allow_opus_but_not_fable(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            claude_dir = Path(directory)
            agent_dir = claude_dir / "agents"
            opus_skill_dir = claude_dir / "skills" / "opus-skill"
            fable_skill_dir = claude_dir / "skills" / "fable-skill"
            agent_dir.mkdir()
            opus_skill_dir.mkdir(parents=True)
            fable_skill_dir.mkdir(parents=True)
            (agent_dir / "opus-agent.md").write_text(
                "---\nname: opus-agent\nmodel: opus\n---\n\nUse Opus.\n",
                encoding="utf-8",
            )
            (opus_skill_dir / "SKILL.md").write_text(
                "---\nname: opus-skill\nmodel: opus\n---\n\nUse Opus.\n",
                encoding="utf-8",
            )
            (agent_dir / "fable-agent.md").write_text(
                "---\nname: fable-agent\nmodel: fable\n---\n\nUse Fable.\n",
                encoding="utf-8",
            )
            (fable_skill_dir / "SKILL.md").write_text(
                "---\nname: fable-skill\nmodel: fable\n---\n\nUse Fable.\n",
                encoding="utf-8",
            )

            previous = routing.CLAUDE_DIR
            routing.CLAUDE_DIR = claude_dir
            try:
                responses = [
                    routing.evaluate(
                        {
                            "prompt": "Handle the hard task",
                            "description": "Delegate work",
                            "subagent_type": subagent,
                            "model": model,
                        }
                    )
                    for subagent, model in (
                        ("opus-agent", "opus"),
                        ("opus-skill", "opus"),
                        ("fable-agent", "fable"),
                        ("fable-skill", "fable"),
                    )
                ]
            finally:
                routing.CLAUDE_DIR = previous

        self.assertEqual(responses[:2], [None, None])
        for response in responses[2:]:
            output = specific(response)
            self.assertEqual(output["permissionDecision"], "allow")
            self.assertEqual(output["updatedInput"]["model"], "sonnet")

    def test_project_settings_do_not_globally_force_subagent_model(self) -> None:
        settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        subagent_model = settings.get("env", {}).get("CLAUDE_CODE_SUBAGENT_MODEL")

        self.assertEqual(settings.get("model"), "sonnet")
        self.assertNotIn("opus", settings.get("fallbackModel", []))
        self.assertIn(subagent_model, (None, "inherit"))


class InputValidationTests(unittest.TestCase):
    def test_non_agent_and_invalid_input_are_ignored(self) -> None:
        self.assertEqual(run_hook({}, tool_name="Read"), {})
        self.assertEqual(run_hook("not-an-object"), {})
        self.assertIsNone(
            routing.evaluate(
                {
                    "prompt": "Analyze this module",
                    "subagent_type": "Explore",
                    "model": "haiku",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
