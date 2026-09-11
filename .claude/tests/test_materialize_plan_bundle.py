import importlib.util
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / "skills"
    / "planner"
    / "scripts"
    / "materialize_plan_bundle.py"
)
SPEC = importlib.util.spec_from_file_location("materialize_plan_bundle", SCRIPT)
materializer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(materializer)


def bundle(task_body: str, schema: int = 4) -> str:
    baseline = "" if schema == 3 else """## Repository baselines

- `/workspace/project`: fetched `origin/main` at `abc1234` on `feature`; worktree clean.

"""
    return f"""# Plan bundle: Test

Target: plans/test/

## File: PLAN.md

```markdown
# Test

Plan schema: {schema}

{baseline}## Objective

Test the plan contract.

## Risks and resolutions

- None — explicit assumption and prospective-failure audit found no material risk.

## Execution order

Blocks: t1-test

## Task index

- `t1-test`: `tasks/t1-test.md`
```

## File: tasks/t1-test.md

```markdown
{task_body.rstrip()}
```
"""


TASK_4 = """# t1-test

Status: PENDING
Model: sonnet
Model reason: Bounded source implementation requires Sonnet.
Skills: example:domain
Skill context: Mode resolved by planner.
Goal: Make the artifact ready.
Writes: pom.xml
How: Change the pinned dependency.
Materialization: Local — CLAUDE_PLAN_MATERIALIZATION=1 ./mvnw install -DskipTests creates version 1 locally.
Handoff: Version 1 is resolvable by the consumer.
Verification: CI — ./mvnw verify passes.
Results:
"""


class MaterializePlanBundleTests(unittest.TestCase):
    def test_schema_4_accepts_sequencing_fields(self):
        target, files = materializer.parse_bundle(bundle(TASK_4))
        self.assertEqual("plans/test", str(target))
        self.assertEqual(2, len(files))

    def test_schema_4_rejects_unknown_task_field(self):
        body = TASK_4.replace("Goal:", "Blocks: t0-other\nGoal:")
        with self.assertRaisesRegex(materializer.BundleError, "unknown"):
            materializer.parse_bundle(bundle(body))

    def test_schema_4_rejects_invalid_skill_invocation(self):
        body = TASK_4.replace("example:domain", "Example Domain")
        with self.assertRaisesRegex(materializer.BundleError, "invalid Skills"):
            materializer.parse_bundle(bundle(body))

    def test_schema_4_rejects_haiku_implementation(self):
        body = TASK_4.replace(
            "Model: sonnet\nModel reason: Bounded source implementation requires Sonnet.",
            "Model: haiku",
        )
        with self.assertRaisesRegex(materializer.BundleError, "Writes to Haiku"):
            materializer.parse_bundle(bundle(body))

    def test_schema_4_requires_a_concrete_fetched_baseline(self):
        content = bundle(TASK_4).replace("fetched `origin/main` at `abc1234`", "uses the current branch")
        with self.assertRaisesRegex(materializer.BundleError, "fetched ref and commit"):
            materializer.parse_bundle(content)

    def test_pending_task_must_have_empty_results(self):
        body = TASK_4 + "Outcome: complete\n"
        with self.assertRaisesRegex(materializer.BundleError, "PENDING"):
            materializer.parse_bundle(bundle(body))

    def test_skill_context_and_broad_materialization_are_guarded(self):
        context_without_skill = TASK_4.replace(
            "Skills: example:domain", "Skills: None"
        )
        unmarked = TASK_4.replace(
            "CLAUDE_PLAN_MATERIALIZATION=1 ./mvnw install -DskipTests",
            "./mvnw install",
        )
        with self.assertRaisesRegex(materializer.BundleError, "Skill context"):
            materializer.parse_bundle(bundle(context_without_skill))
        with self.assertRaisesRegex(materializer.BundleError, "explicit marker"):
            materializer.parse_bundle(bundle(unmarked))

    def test_done_manual_task_cannot_still_be_pending(self):
        body = (
            TASK_4.replace("Status: PENDING", "Status: DONE")
            .replace("Verification: CI", "Verification: Manual")
            + "Verification: pending Manual review\n"
        )
        with self.assertRaisesRegex(materializer.BundleError, "pending Manual"):
            materializer.parse_bundle(bundle(body))

    def test_schema_3_remains_read_compatible(self):
        old = """# t1-test

Status: PENDING
Model: haiku
Skills: None
Goal: Inspect the artifact.
Writes: None
How: Read the specified file.
Verification: Manual — User reviews the result.
Results:
"""
        materializer.parse_bundle(bundle(old, schema=3))


if __name__ == "__main__":
    unittest.main()
