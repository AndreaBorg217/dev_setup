import importlib.util
import tempfile
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
bundle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bundle)


def staging(
    task_path="tasks/t1-do-work.md",
    task_heading="t1-do-work",
    manifest_extra="",
    task_extra="",
    verification="CI — python3 -m unittest tests.test_one",
    writes="None",
):
    return f"""# Plan bundle: Example

Target: plans/example/

## File: PLAN.md

```markdown
# Example

Plan schema: 3

## Objective

Do the work.

## Boundaries and decisions

- Decision: CI owns runtime verification.
{manifest_extra}

## Execution order

Blocks: t1-do-work

## Task index

- `t1-do-work`: `{task_path}`
```

## File: {task_path}

```markdown
# {task_heading}

Status: PENDING
Model: haiku
Skills: None
Goal: Do the work.
Writes: {writes}
How: Inspect it.
Verification: {verification}
Results:
{task_extra}
```
"""


class PlanBundleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.staging = self.root / "staging.md"

    def tearDown(self):
        self.temporary.cleanup()

    def test_materializes_exact_split_files(self):
        self.staging.write_text(staging(), encoding="utf-8")

        destination, count = bundle.materialize(self.staging, self.root)

        self.assertEqual(2, count)
        self.assertEqual((self.root / "plans" / "example").resolve(), destination)
        self.assertIn("Plan schema: 3", (destination / "PLAN.md").read_text())
        task = (destination / "tasks" / "t1-do-work.md").read_text()
        self.assertTrue(task.startswith("# t1-do-work\n"))

    def test_rejects_path_traversal(self):
        self.staging.write_text(
            staging("tasks/../outside.md", "outside"), encoding="utf-8"
        )

        with self.assertRaisesRegex(bundle.BundleError, "unsafe relative path"):
            bundle.materialize(self.staging, self.root)

    def test_rejects_index_heading_mismatch_before_writing(self):
        self.staging.write_text(staging(task_heading="wrong"), encoding="utf-8")

        with self.assertRaisesRegex(bundle.BundleError, "heading does not match"):
            bundle.materialize(self.staging, self.root)
        self.assertFalse((self.root / "plans").exists())

    def test_rejects_assumptions_and_broad_local_suites(self):
        cases = [
            (
                staging(manifest_extra="- Assumption: Maven defaults are suitable."),
                "Assumption entries are forbidden",
            ),
            (
                staging(verification="Local — mvn test"),
                "Local verification is a broad test suite",
            ),
            (
                staging(verification="Local — mvn clean compile"),
                "Local verification is a broad test suite",
            ),
        ]
        for content, error in cases:
            with self.subTest(error=error):
                self.staging.write_text(content, encoding="utf-8")
                with self.assertRaisesRegex(bundle.BundleError, error):
                    bundle.validate(self.staging, self.root)

    def test_rejects_sonnet_without_a_model_reason(self):
        self.staging.write_text(
            staging().replace("Model: haiku", "Model: sonnet"), encoding="utf-8"
        )

        with self.assertRaisesRegex(bundle.BundleError, "requires one non-empty Model reason"):
            bundle.validate(self.staging, self.root)

    def test_rejects_duplicate_write_ownership(self):
        second = staging(writes="src/Main.java").replace(
            "Blocks: t1-do-work",
            "Blocks: t1-do-work >> t2-more-work",
        ).replace(
            "- `t1-do-work`: `tasks/t1-do-work.md`",
            "- `t1-do-work`: `tasks/t1-do-work.md`\n- `t2-more-work`: `tasks/t2-more-work.md`",
        )
        second += """

## File: tasks/t2-more-work.md

```markdown
# t2-more-work

Status: PENDING
Model: haiku
Skills: coding
Goal: Do more work.
Writes: src/Main.java
How: Make the approved edit.
Verification: CI — python3 -m unittest tests.test_two
Results:
```
"""
        self.staging.write_text(second, encoding="utf-8")

        with self.assertRaisesRegex(bundle.BundleError, "owned by both"):
            bundle.validate(self.staging, self.root)


if __name__ == "__main__":
    unittest.main()
