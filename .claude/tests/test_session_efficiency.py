import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / "skills"
    / "session-efficiency-reviewer"
    / "scripts"
    / "session_efficiency.py"
)
SPEC = importlib.util.spec_from_file_location("session_efficiency", SCRIPT)
reviewer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reviewer)


class TranscriptFixture:
    def __init__(self, path, cwd):
        self.path = path
        self.cwd = str(cwd)
        self.events = []

    def tool(self, request, tool_id, name, tool_input, model="claude-opus-4-6", usage=None):
        self.events.append(
            {
                "type": "assistant",
                "cwd": self.cwd,
                "requestId": request,
                "message": {
                    "model": model,
                    "usage": usage or {"output_tokens": 10},
                    "content": [
                        {
                            "type": "tool_use",
                            "id": tool_id,
                            "name": name,
                            "input": tool_input,
                        }
                    ],
                },
            }
        )

    def assistant(
        self,
        request,
        model="claude-sonnet-5",
        skill=None,
        output_tokens=5,
        usage=None,
        timestamp=None,
    ):
        event = {
            "type": "assistant",
            "cwd": self.cwd,
            "requestId": request,
            "message": {
                "model": model,
                "usage": usage or {"output_tokens": output_tokens},
                "content": [{"type": "text", "text": "private assistant content"}],
            },
        }
        if skill:
            event["attributionSkill"] = skill
        if timestamp:
            event["timestamp"] = timestamp
        self.events.append(event)

    def result(self, tool_id, content, file_meta=None, tool_result=None, is_error=False):
        event = {
            "type": "user",
            "cwd": self.cwd,
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": content,
                        "is_error": is_error,
                    }
                ],
            },
        }
        if tool_result is not None:
            event["toolUseResult"] = tool_result
        elif file_meta:
            event["toolUseResult"] = {"type": "text", "file": file_meta}
        self.events.append(event)

    def write(self, malformed=False):
        with self.path.open("w", encoding="utf-8") as handle:
            for event in self.events:
                handle.write(json.dumps(event) + "\n")
            if malformed:
                handle.write("{not-json\n")


class SessionEfficiencyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.transcript = self.root / "session.jsonl"

    def tearDown(self):
        self.temporary.cleanup()

    def test_requested_antipatterns_are_detected_without_content_leaks(self):
        skill = self.root / ".claude" / "skills" / "foo"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("skill instruction\n" * 100, encoding="utf-8")
        fixture = TranscriptFixture(self.transcript, self.root)
        big_file = self.root / "src" / "sensitive-name.py"

        for index in range(3):
            tool_id = f"read-{index}"
            fixture.tool(f"search-{index}", tool_id, "Read", {"file_path": str(big_file)})
            fixture.result(
                tool_id,
                "PRIVATE_FILE_CONTENT" * 20,
                {"totalLines": 1201, "numLines": 1201, "startLine": 1},
            )
        for index, command in enumerate(("rg TODO .", "find . -name '*.py'", "git status")):
            tool_id = f"bash-{index}"
            fixture.tool(f"bash-request-{index}", tool_id, "Bash", {"command": command})
            fixture.result(tool_id, "PRIVATE_BASH_OUTPUT")
        fixture.tool("payload", "mcp-1", "mcp__warehouse__query", {"query": "private"})
        fixture.result("mcp-1", {"secret": "DO_NOT_LEAK" * 50})
        fixture.tool("skill-call", "skill-1", "Skill", {"skill": "foo"}, model="claude-sonnet-5")
        fixture.result("skill-1", "skill loaded")
        fixture.assistant("skill-output", skill="foo", output_tokens=5)
        fixture.write()

        parsed = reviewer.parse_transcripts([self.transcript])
        report = reviewer.analyze(
            parsed,
            reviewer.Thresholds(
                large_file_lines=1000,
                oversized_tool_bytes=100,
                repeat_reads=3,
                expensive_search_turns=3,
                bash_calls=3,
                large_skill_tokens=100,
                skill_output_ratio=0.5,
                chars_per_token=4,
            ),
        )

        categories = {item["category"] for item in report["warnings"]}
        self.assertEqual(
            {
                "large_direct_reads",
                "repeated_file_read",
                "expensive_model_repo_search",
                "oversized_tool_payload",
                "chatty_bash",
                "oversized_underused_skill",
                "missing_coding_skill",
                "missing_git_skill",
            },
            categories,
        )
        rendered = reviewer.render_text(report)
        serialized = json.dumps(report)
        for secret in (
            "PRIVATE_FILE_CONTENT",
            "PRIVATE_BASH_OUTPUT",
            "DO_NOT_LEAK",
            "rg TODO",
            "private assistant content",
        ):
            self.assertNotIn(secret, rendered)
            self.assertNotIn(secret, serialized)
        self.assertIn("src/sensitive-name.py", rendered)

    def test_streamed_records_count_request_usage_once(self):
        fixture = TranscriptFixture(self.transcript, self.root)
        fixture.assistant("same-request", skill="foo", output_tokens=300)
        fixture.assistant("same-request", skill="foo", output_tokens=300)
        fixture.write()

        parsed = reviewer.parse_transcripts([self.transcript])

        self.assertEqual(1, len(parsed["requests"]))
        self.assertEqual(300, parsed["requests"][0]["output_tokens"])

    def test_high_context_replay_normalizes_usage_schema_variants(self):
        fixture = TranscriptFixture(self.transcript, self.root)
        fixture.assistant(
            "snake",
            usage={
                "output_tokens": 1,
                "input_tokens": 2,
                "cache_read_input_tokens": 120,
                "cache_creation_input_tokens": 10,
            },
        )
        fixture.assistant(
            "camel",
            usage={
                "output_tokens": 1,
                "inputTokens": 3,
                "cacheReadInputTokens": 130,
                "cacheCreationInputTokens": 11,
            },
        )
        fixture.assistant(
            "nested",
            usage={
                "output_tokens": 1,
                "input_tokens": 4,
                "input_tokens_details": {"cached_tokens": 140},
                "cache_creation": {"ephemeral_1h_input_tokens": 12},
            },
        )
        fixture.write()

        report = reviewer.analyze(
            reviewer.parse_transcripts([self.transcript]),
            reviewer.Thresholds(high_context_tokens=100, high_context_requests=3),
        )

        high_context = next(
            item for item in report["warnings"] if item["category"] == "high_context_replay"
        )
        self.assertEqual(390, high_context["evidence"]["cache_read_input_tokens"])
        self.assertEqual(33, high_context["evidence"]["cache_creation_input_tokens"])
        self.assertEqual(9, high_context["evidence"]["input_tokens"])
        self.assertEqual(432, report["summary"]["context_input_tokens"])

    def test_sonnet_repo_search_is_a_routing_candidate(self):
        fixture = TranscriptFixture(self.transcript, self.root)
        for index in range(2):
            fixture.tool(
                f"request-{index}",
                f"read-{index}",
                "Read",
                {"file_path": str(self.root / f"file-{index}.py")},
                model="claude-sonnet-5",
            )
            fixture.result(f"read-{index}", "small")
        fixture.write()

        report = reviewer.analyze(
            reviewer.parse_transcripts([self.transcript]),
            reviewer.Thresholds(expensive_search_turns=2),
        )

        routing = next(
            item
            for item in report["warnings"]
            if item["category"] == "expensive_model_repo_search"
        )
        self.assertEqual(["claude-sonnet-5"], routing["evidence"]["models"])
        self.assertEqual({"main": 2}, routing["evidence"]["trace_roles"])
        self.assertEqual({"Read (broad)": 2}, routing["evidence"]["search_operations"])

    def test_repository_search_reports_command_names_without_arguments(self):
        fixture = TranscriptFixture(self.transcript, self.root)
        fixture.tool(
            "request",
            "bash",
            "Bash",
            {"command": "rg private-pattern src && git status --short | head -5"},
            model="claude-sonnet-5",
        )
        fixture.result("bash", "small")
        fixture.write()

        report = reviewer.analyze(
            reviewer.parse_transcripts([self.transcript]),
            reviewer.Thresholds(expensive_search_turns=1),
        )
        routing = next(
            item
            for item in report["warnings"]
            if item["category"] == "expensive_model_repo_search"
        )

        self.assertEqual(
            {"head": 1, "rg": 1},
            routing["evidence"]["bash_search_commands"],
        )
        self.assertNotIn("private-pattern", json.dumps(routing))

    def test_resolved_model_overrides_incorrect_child_transcript_label(self):
        fixture = TranscriptFixture(self.transcript, self.root)
        fixture.tool(
            "agent-call",
            "agent-tool",
            "Agent",
            {"model": "sonnet", "prompt": "DO_NOT_REPORT_PROMPT"},
            model="claude-opus-4-6",
        )
        fixture.result(
            "agent-tool",
            "DO_NOT_REPORT_RESULT",
            tool_result={"agentId": "abc123", "resolvedModel": "claude-sonnet-5"},
        )
        fixture.write()
        child_dir = self.root / self.transcript.stem / "subagents"
        child_dir.mkdir(parents=True)
        child = TranscriptFixture(child_dir / "agent-abc123.jsonl", self.root)
        child.assistant("child-request", model="claude-opus-4-6")
        child.write()

        report = reviewer.analyze(
            reviewer.parse_transcripts(reviewer.review_paths(self.transcript))
        )

        self.assertNotIn(
            "agent_model_mismatch", {item["category"] for item in report["warnings"]}
        )
        self.assertEqual(1, report["summary"]["models"]["claude-sonnet-5"])
        self.assertEqual(
            {
                "requested_models": {"sonnet": 1},
                "resolved_models": {"claude-sonnet-5": 1},
                "subagent_types": {"<unset>": 1},
            },
            report["summary"]["agent_dispatches"],
        )
        serialized = json.dumps(report)
        self.assertNotIn("abc123", serialized)
        self.assertNotIn("DO_NOT_REPORT", serialized)

    def test_unidentified_agent_to_child_association_is_labelled_heuristic(self):
        fixture = TranscriptFixture(self.transcript, self.root)
        fixture.tool(
            "agent-call",
            "agent-tool",
            "Agent",
            {"model": "sonnet", "prompt": "private"},
        )
        fixture.result("agent-tool", "private", tool_result={"status": "completed"})
        fixture.write()
        child_dir = self.root / self.transcript.stem / "subagents"
        child_dir.mkdir(parents=True)
        child = TranscriptFixture(child_dir / "agent-unmatched.jsonl", self.root)
        child.assistant("child-request", model="claude-opus-4-6")
        child.write()

        report = reviewer.analyze(
            reviewer.parse_transcripts(reviewer.review_paths(self.transcript))
        )
        mismatch = next(
            item for item in report["warnings"] if item["category"] == "agent_model_mismatch"
        )

        self.assertEqual("heuristic", mismatch["evidence"]["association"])

    def test_resolved_model_mismatch_is_reported_authoritatively(self):
        fixture = TranscriptFixture(self.transcript, self.root)
        fixture.tool(
            "agent-call",
            "agent-tool",
            "Agent",
            {"model": "haiku", "prompt": "private"},
        )
        fixture.result(
            "agent-tool",
            "private",
            tool_result={"agentId": "abc123", "resolvedModel": "claude-sonnet-5"},
        )
        fixture.write()

        report = reviewer.analyze(reviewer.parse_transcripts([self.transcript]))

        mismatch = next(
            item for item in report["warnings"] if item["category"] == "agent_model_mismatch"
        )
        self.assertEqual("resolvedModel", mismatch["evidence"]["association"])
        self.assertEqual({"haiku": 1}, mismatch["evidence"]["requested_tiers"])
        self.assertEqual({"sonnet": 1}, mismatch["evidence"]["resolved_runtime_tiers"])

    def test_denied_and_non_overlapping_reads_are_not_counted_as_repeats(self):
        fixture = TranscriptFixture(self.transcript, self.root)
        source = self.root / "src" / "Large.java"
        ranges = [(1, 100), (101, 100), (201, 100), (301, 100)]
        for index, (offset, limit) in enumerate(ranges):
            fixture.tool(
                f"request-{index}",
                f"read-{index}",
                "Read",
                {"file_path": str(source), "offset": offset, "limit": limit},
            )
            fixture.result(f"read-{index}", "small result")
        fixture.tool(
            "denied",
            "read-denied",
            "Read",
            {"file_path": str(source)},
        )
        fixture.result(
            "read-denied",
            "Required skill not loaded for a mutating or verification tool",
            is_error=True,
        )
        fixture.write()

        report = reviewer.analyze(
            reviewer.parse_transcripts([self.transcript]),
            reviewer.Thresholds(repeat_reads=3),
        )

        self.assertNotIn(
            "repeated_file_read", {item["category"] for item in report["warnings"]}
        )

    def test_list_and_safe_touch_filter_include_subagent_traces(self):
        transcript_root = self.root / "projects"
        project = self.root / "work" / "repo"
        project_dir = transcript_root / reviewer.project_key(project)
        project_dir.mkdir(parents=True)
        older = project_dir / "older.jsonl"
        newer = project_dir / "newer.jsonl"
        older_fixture = TranscriptFixture(older, project)
        older_fixture.assistant("older-request")
        older_fixture.write()
        newer_fixture = TranscriptFixture(newer, project)
        newer_fixture.assistant("newer-request")
        newer_fixture.write()
        os.utime(older, (1, 1))
        os.utime(newer, (2, 2))

        target = project / "plans" / "case" / "PROBLEM.md"
        subagents = project_dir / "newer" / "subagents"
        subagents.mkdir(parents=True)
        child = TranscriptFixture(subagents / "agent.jsonl", project)
        child.tool("write", "write-1", "Write", {"file_path": str(target), "content": "private"})
        child.write()

        listed = reviewer.list_transcripts(project, transcript_root, 5)

        self.assertEqual([newer, older], listed)
        self.assertTrue(reviewer.transcript_touches(newer, target, project))
        self.assertFalse(reviewer.transcript_touches(older, target, project))
        self.assertEqual(2, len(reviewer.review_paths(newer)))
        key = reviewer.project_key(Path("/tmp/repo.with.dots/and_name"))
        self.assertTrue(key.endswith("-repo-with-dots-and-name"))
        self.assertNotIn("_", key)

    def test_latest_ignores_newer_clear_only_transcript(self):
        transcript_root = self.root / "projects"
        project = self.root / "work" / "repo"
        project_dir = transcript_root / reviewer.project_key(project)
        project_dir.mkdir(parents=True)
        substantive = project_dir / "substantive.jsonl"
        cleared = project_dir / "cleared.jsonl"

        fixture = TranscriptFixture(substantive, project)
        fixture.assistant("request")
        fixture.write()
        cleared.write_text(
            json.dumps(
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": "<command-name>/clear</command-name>",
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        os.utime(substantive, (1, 1))
        os.utime(cleared, (2, 2))

        self.assertEqual(
            [substantive], reviewer.list_transcripts(project, transcript_root, 5)
        )

    def test_default_thresholds_flag_one_large_read_and_aggregate_output(self):
        fixture = TranscriptFixture(self.transcript, self.root)
        source = self.root / "large.yml"
        fixture.tool("read-request", "read", "Read", {"file_path": str(source)})
        fixture.result("read", "x" * 25_000, {"totalLines": 350})
        fixture.tool(
            "query-request", "query", "Bash", {"command": "curl --max-time 10 URL"}
        )
        fixture.result("query", "y" * 25_000)
        fixture.write()

        report = reviewer.analyze(reviewer.parse_transcripts([self.transcript]))
        categories = {item["category"] for item in report["warnings"]}

        self.assertIn("large_direct_reads", categories)
        self.assertIn("oversized_tool_payload", categories)
        self.assertIn("aggregate_tool_output", categories)

    def test_malformed_lines_are_counted_not_printed(self):
        fixture = TranscriptFixture(self.transcript, self.root)
        fixture.assistant("request")
        fixture.write(malformed=True)

        report = reviewer.analyze(reviewer.parse_transcripts([self.transcript]))

        self.assertEqual(1, report["summary"]["invalid_lines"])
        self.assertIn("Skipped malformed", reviewer.render_text(report))

    def test_cli_json_contains_aggregates_only(self):
        fixture = TranscriptFixture(self.transcript, self.root)
        fixture.assistant("request")
        fixture.write()
        output = io.StringIO()

        with redirect_stdout(output):
            result = reviewer.main(["review", str(self.transcript), "--json", "--main-only"])

        self.assertEqual(0, result)
        payload = json.loads(output.getvalue())
        self.assertEqual(1, payload["summary"]["model_requests"])
        self.assertNotIn("private assistant content", output.getvalue())

    def test_continuations_and_agent_volume_are_neutral_without_duplication(self):
        fixture = TranscriptFixture(self.transcript, self.root)
        fixture.tool(
            "verify-agent",
            "agent-1",
            "Agent",
            {"subagent_type": "verifier", "model": "haiku", "prompt": "private"},
        )
        fixture.result("agent-1", "completed")
        for index in range(2):
            tool_id = f"continue-{index}"
            fixture.tool(
                f"continue-request-{index}",
                tool_id,
                "SendMessage",
                {"recipient": "private", "content": "private"},
            )
            fixture.result(tool_id, "sent")
        for index in range(2):
            tool_id = f"broad-test-{index}"
            fixture.tool(
                f"broad-test-request-{index}",
                tool_id,
                "Bash",
                {"command": "mvn test"},
            )
            fixture.result(tool_id, "failed", is_error=True)
        fixture.tool(
            "targeted-test",
            "bash-2",
            "Bash",
            {"command": "mvn -Dtest=TopologyTest test"},
        )
        fixture.result("bash-2", "passed")
        fixture.tool(
            "denied-read",
            "read-1",
            "Read",
            {"file_path": str(self.root / "Large.java")},
        )
        fixture.result(
            "read-1",
            "Read can expose more than 400 lines; run shunt.py read",
            is_error=True,
        )
        fixture.write()

        report = reviewer.analyze(reviewer.parse_transcripts([self.transcript]))
        categories = {item["category"] for item in report["warnings"]}

        self.assertTrue(
            {
                "repeated_broad_verification",
                "shunt_bypassed_after_denial",
            }.issubset(categories)
        )
        self.assertNotIn("dedicated_verifier", categories)
        self.assertNotIn("subagent_continuation_churn", categories)
        self.assertNotIn("unbounded_subagent", categories)
        self.assertEqual(
            {"broad": 2, "targeted": 1},
            report["summary"]["verification_commands"],
        )
        self.assertEqual(
            {"read": 0, "write": 0, "denied_reads": 1},
            report["summary"]["shunt"],
        )

    def test_long_trace_fix_does_not_recommend_turn_caps(self):
        fixture = TranscriptFixture(self.transcript, self.root)
        for index in range(3):
            fixture.assistant(f"request-{index}")
        fixture.write()

        report = reviewer.analyze(
            reviewer.parse_transcripts([self.transcript]),
            reviewer.Thresholds(max_main_requests=2),
        )
        warning = next(
            item
            for item in report["warnings"]
            if item["category"] == "excessive_main_requests"
        )

        self.assertNotIn("maxTurns", warning["fix"])

    def test_cross_trace_file_access_is_an_ownership_violation(self):
        child_path = self.root / "agent-owner.jsonl"
        source = self.root / "src" / "shared.py"
        main = TranscriptFixture(self.transcript, self.root)
        child = TranscriptFixture(child_path, self.root)
        for fixture, prefix in ((main, "main"), (child, "child")):
            fixture.tool(prefix, f"{prefix}-read", "Read", {"file_path": str(source)})
            fixture.result(f"{prefix}-read", "bounded source")
            fixture.write()

        report = reviewer.analyze(
            reviewer.parse_transcripts([self.transcript, child_path])
        )
        ownership = next(
            item
            for item in report["warnings"]
            if item["category"] == "file_ownership_violation"
        )

        self.assertEqual(["src/shared.py"], ownership["evidence"]["files"])
        self.assertEqual(2, ownership["evidence"]["traces"])

    def test_long_subagent_is_not_labelled_waste_without_duplication(self):
        child_path = self.root / "agent-long.jsonl"
        main = TranscriptFixture(self.transcript, self.root)
        main.assistant("main")
        main.write()
        child = TranscriptFixture(child_path, self.root)
        for index in range(12):
            child.assistant(f"child-{index}", model="claude-haiku-4-5")
        child.write()

        categories = {
            item["category"]
            for item in reviewer.analyze(
                reviewer.parse_transcripts([self.transcript, child_path]),
                reviewer.Thresholds(max_subagent_requests=2),
            )["warnings"]
        }

        self.assertNotIn("unbounded_subagent", categories)

    def test_sustained_main_collection_without_agent_is_missed_delegation(self):
        fixture = TranscriptFixture(self.transcript, self.root)
        for index in range(8):
            fixture.tool(
                f"query-{index}",
                f"query-tool-{index}",
                "mcp__warehouse__run_query",
                {"query": "private"},
            )
            fixture.result(f"query-tool-{index}", "bounded result")
        fixture.write()

        report = reviewer.analyze(reviewer.parse_transcripts([self.transcript]))
        missed = next(
            item
            for item in report["warnings"]
            if item["category"] == "missed_delegation"
        )

        self.assertEqual(8, missed["evidence"]["calls"])
        self.assertEqual(
            {"data or external sources": 8},
            missed["evidence"]["tool_families"],
        )
        self.assertNotIn("private", json.dumps(missed))

    def test_agent_dispatch_makes_main_collection_neutral(self):
        fixture = TranscriptFixture(self.transcript, self.root)
        fixture.tool(
            "agent",
            "agent-tool",
            "Agent",
            {"subagent_type": "explorer", "model": "haiku", "prompt": "private"},
        )
        fixture.result("agent-tool", "bounded result")
        for index in range(8):
            fixture.tool(
                f"query-{index}",
                f"query-tool-{index}",
                "mcp__warehouse__run_query",
                {"query": "private"},
            )
            fixture.result(f"query-tool-{index}", "bounded result")
        fixture.write()

        categories = {
            item["category"]
            for item in reviewer.analyze(
                reviewer.parse_transcripts([self.transcript])
            )["warnings"]
        }

        self.assertNotIn("missed_delegation", categories)

    def test_context_mode_collection_in_main_trace_is_not_missed_delegation(self):
        fixture = TranscriptFixture(self.transcript, self.root)
        for index in range(8):
            fixture.tool(
                f"context-{index}",
                f"context-tool-{index}",
                "mcp__plugin_context-mode_context-mode__ctx_execute",
                {"language": "shell", "code": "private"},
            )
            fixture.result(f"context-tool-{index}", "bounded result")
        fixture.write()

        categories = {
            item["category"]
            for item in reviewer.analyze(
                reviewer.parse_transcripts([self.transcript])
            )["warnings"]
        }

        self.assertNotIn("missed_delegation", categories)

    def test_skill_adherence_is_checked_per_trace(self):
        airflow_source = self.root / "airflow" / "dags" / "job.py"
        fixture = TranscriptFixture(self.transcript, self.root)
        fixture.tool("read", "read-1", "Read", {"file_path": str(airflow_source)})
        fixture.result("read-1", "source")
        fixture.tool("git", "git-1", "Bash", {"command": "git status --short"})
        fixture.result("git-1", "clean")
        fixture.write()

        categories = {
            item["category"]
            for item in reviewer.analyze(
                reviewer.parse_transcripts([self.transcript])
            )["warnings"]
        }

        self.assertTrue(
            {
                "missing_coding_skill",
                "missing_airflow_skill",
                "missing_git_skill",
            }.issubset(categories)
        )

    def test_loaded_skills_satisfy_adherence_checks(self):
        source = self.root / "airflow" / "dags" / "job.py"
        fixture = TranscriptFixture(self.transcript, self.root)
        for index, skill in enumerate(("coding", "airflow", "git")):
            fixture.tool(f"skill-{index}", f"skill-tool-{index}", "Skill", {"skill": skill})
            fixture.result(f"skill-tool-{index}", "loaded")
        fixture.tool("read", "read-1", "Read", {"file_path": str(source)})
        fixture.result("read-1", "source")
        fixture.tool("git", "git-1", "Bash", {"command": "git status --short"})
        fixture.result("git-1", "clean")
        fixture.write()

        categories = {
            item["category"]
            for item in reviewer.analyze(
                reviewer.parse_transcripts([self.transcript])
            )["warnings"]
        }

        self.assertFalse(
            {
                "missing_coding_skill",
                "missing_airflow_skill",
                "missing_git_skill",
            }
            & categories
        )

    def test_review_day_selects_local_date_and_aggregates_sessions(self):
        transcript_root = self.root / "projects"
        project = self.root / "repo"
        project_dir = transcript_root / reviewer.project_key(project)
        project_dir.mkdir(parents=True)
        first = project_dir / "first.jsonl"
        second = project_dir / "second.jsonl"
        outside = project_dir / "outside.jsonl"
        for path, timestamp in (
            (first, "2026-09-17T08:00:00+02:00"),
            (second, "2026-09-17T20:00:00+02:00"),
            (outside, "2026-09-18T08:00:00+02:00"),
        ):
            fixture = TranscriptFixture(path, project)
            fixture.assistant(path.stem, timestamp=timestamp)
            fixture.write()

        timezone = reviewer.ZoneInfo("Europe/Malta")
        selected = reviewer.day_transcripts(
            transcript_root,
            reviewer.date(2026, 9, 17),
            timezone,
            [project],
        )
        report = reviewer.review_day(selected)

        self.assertEqual([first, second], selected)
        self.assertEqual(2, report["summary"]["sessions"])
        self.assertEqual(2, report["summary"]["model_requests"])


if __name__ == "__main__":
    unittest.main()
