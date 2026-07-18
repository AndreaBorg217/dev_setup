#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any


HOOKS_DIR = Path(__file__).resolve().parent.parent
HOOK_PATH = HOOKS_DIR / "subagent-routing.py"


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
    def test_missing_model_rewrites_confident_general_purpose_and_preserves_input(self) -> None:
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
            ("haiku", "Plan", "Find test files", "sonnet"),
            ("sonnet", "Explore", "Analyze the module", "haiku"),
        )
        for model, agent, prompt, expected in cases:
            with self.subTest(model=model, agent=agent):
                output = specific(run_hook({
                    "prompt": prompt,
                    "description": "Delegate work",
                    "subagent_type": agent,
                    "model": model,
                }))
                self.assertEqual(output["permissionDecision"], "allow")
                self.assertEqual(output["updatedInput"]["model"], expected)

    def test_case_insensitive_builtin_names_and_confident_general_purpose_routes(self) -> None:
        cases = (
            ("GeNeRaL-PuRpOsE", "Create an implementation plan", "Plan", "sonnet"),
            ("general-purpose", "Plan the implementation", "Plan", "sonnet"),
            ("GENERAL-PURPOSE", "Fix the parser", "caveman:cavecrew-builder", "sonnet"),
            ("general-purpose", "Review this diff", "caveman:cavecrew-reviewer", "haiku"),
            ("eXpLoRe", "Where is WidgetFactory?", "caveman:cavecrew-investigator", "haiku"),
            ("Explore", "Find the parser test files", "caveman:cavecrew-investigator", "haiku"),
        )
        for agent, prompt, expected_agent, expected_model in cases:
            with self.subTest(agent=agent, prompt=prompt):
                output = specific(run_hook({
                    "prompt": prompt,
                    "description": "Delegate work",
                    "subagent_type": agent,
                    "model": "inherit",
                }))
                self.assertEqual(output["updatedInput"]["subagent_type"], expected_agent)
                self.assertEqual(output["updatedInput"]["model"], expected_model)

    def test_ambiguous_general_purpose_is_retained_with_cheap_model(self) -> None:
        tool_input = {
            "prompt": "Handle this bounded task",
            "description": "Delegate work",
            "subagent_type": "general-purpose",
            "model": "sonnet",
        }

        output = specific(run_hook(tool_input))

        self.assertEqual(output["updatedInput"]["subagent_type"], "general-purpose")
        self.assertEqual(output["updatedInput"]["model"], "haiku")

    def test_agent_role_takes_precedence_over_conflicting_prompt_keywords(self) -> None:
        cases = (
            ("caveman:cavecrew-investigator", "Implement a fix", "haiku"),
            ("caveman:cavecrew-builder", "Find all references", "sonnet"),
            ("caveman:cavecrew-reviewer", "Create an implementation plan", "haiku"),
            ("pLaN", "Find all references", "sonnet"),
        )
        for agent, prompt, model in cases:
            with self.subTest(agent=agent):
                response = run_hook({
                    "prompt": prompt,
                    "description": "Conflicting keywords",
                    "subagent_type": agent,
                    "model": model,
                })
                self.assertEqual(response, {})

    def test_correct_inputs_produce_no_hook_output(self) -> None:
        cases = (
            ("Explore", "Analyze this module", "haiku"),
            ("general-purpose", "Handle this bounded task", "haiku"),
            ("custom-agent", "Implement a parser", "sonnet"),
        )
        for agent, prompt, model in cases:
            with self.subTest(agent=agent):
                self.assertEqual(run_hook({
                    "prompt": prompt,
                    "description": "Already routed",
                    "subagent_type": agent,
                    "model": model,
                }), {})


class OpusPermissionTests(unittest.TestCase):
    def test_opus_and_best_ask_with_complete_input_and_preserve_model(self) -> None:
        for model in ("opus", "claude-opus-4-6", "best"):
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

                self.assertEqual(output["permissionDecision"], "ask")
                self.assertEqual(
                    output["updatedInput"],
                    {
                        **tool_input,
                        "subagent_type": "caveman:cavecrew-builder",
                    },
                )
                self.assertEqual(output["updatedInput"]["model"], model)

    def test_opus_ask_includes_unchanged_input_when_no_agent_rewrite_applies(self) -> None:
        tool_input = {
            "prompt": "Create the plan",
            "description": "Plan work",
            "subagent_type": "Plan",
            "model": "opus",
            "resume": "agent-789",
        }

        output = specific(run_hook(tool_input))

        self.assertEqual(output["permissionDecision"], "ask")
        self.assertEqual(output["updatedInput"], tool_input)


class InputValidationTests(unittest.TestCase):
    def test_non_agent_and_invalid_input_are_ignored(self) -> None:
        self.assertEqual(run_hook({}, tool_name="Read"), {})
        self.assertEqual(run_hook("not-an-object"), {})
        self.assertIsNone(routing.evaluate({
            "prompt": "Analyze this module",
            "subagent_type": "Explore",
            "model": "haiku",
        }))


if __name__ == "__main__":
    unittest.main()
