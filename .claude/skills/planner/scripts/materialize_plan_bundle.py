#!/usr/bin/env python3
"""Materialize an approved planner staging bundle without regenerating it."""

from __future__ import annotations

import argparse
import os
import re
import tempfile
from pathlib import Path, PurePosixPath


TARGET = re.compile(r"(?m)^Target: (plans/[a-z0-9][a-z0-9-]*/)$")
FILE_HEADING = re.compile(r"(?m)^## File: ([^\n]+)$")
INDEX_ENTRY = re.compile(r"(?m)^- `([^`]+)`: `([^`]+)`$")
TASK_ID = re.compile(r"t[1-9]\d*-[a-z0-9]+(?:-[a-z0-9]+)*")
STATUS = {"PENDING", "IN_PROGRESS", "DONE", "FAILED", "BLOCKED"}
FIELD = re.compile(r"(?m)^([A-Za-z][A-Za-z ]*):(?: (.*))?$")
PLAN_SCHEMA = re.compile(r"(?m)^Plan schema: ([34])$")
SKILL_NAME = re.compile(r"[a-z0-9][a-z0-9-]*(?::[a-z0-9][a-z0-9-]*)?")


class BundleError(ValueError):
    pass


def safe_relative(raw: str) -> PurePosixPath:
    path = PurePosixPath(raw.strip())
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise BundleError(f"unsafe relative path: {raw}")
    if path != PurePosixPath("PLAN.md") and not (
        len(path.parts) == 2
        and path.parts[0] == "tasks"
        and path.suffix == ".md"
    ):
        raise BundleError(f"unexpected bundle path: {raw}")
    return path


def parse_section(section: str, relative: PurePosixPath) -> str:
    lines = section.strip().splitlines()
    if len(lines) < 3 or lines[0] != "```markdown" or lines[-1] != "```":
        raise BundleError(f"{relative} must have one outer markdown fence")
    content = "\n".join(lines[1:-1]).rstrip() + "\n"
    if not content.strip():
        raise BundleError(f"empty file body: {relative}")
    return content


def single_field(content: str, name: str, task_id: str) -> str:
    values = [value or "" for field, value in FIELD.findall(content) if field == name]
    if len(values) != 1:
        raise BundleError(f"{task_id} must contain exactly one {name} field")
    return values[0].strip()


def local_verification_is_broad(value: str) -> bool:
    lowered = value.lower()
    if re.search(r"\b(?:mvn|mvnw|\./mvnw)\b", lowered):
        return bool(
            re.search(r"\b(?:compile|package|install|test|verify)\b", lowered)
        ) and not any(
            selector in lowered for selector in ("-dtest=", "-dit.test=")
        )
    if re.search(r"\b(?:gradle|gradlew|\./gradlew)\b", lowered):
        return bool(
            re.search(r"\b(?:assemble|build|check|test)\b", lowered)
        ) and "--tests" not in lowered
    if re.search(r"\bgo\s+test\s+\./\.\.\.(?:\s|$)", lowered):
        return True
    if re.search(r"\b(?:npm|pnpm|yarn)\s+(?:run\s+)?test(?:\s|$)", lowered):
        return True
    return bool(
        re.fullmatch(
            r"(?:python(?:3)?\s+-m\s+)?pytest(?:\s+(?:-[a-z0-9-]+))*",
            lowered.strip(),
        )
    )


def validate_manifest(manifest: str, indexed_ids: list[str]) -> int:
    schemas = PLAN_SCHEMA.findall(manifest)
    if len(schemas) != 1:
        raise BundleError("PLAN.md must declare Plan schema: 3 or 4 exactly once")
    schema = int(schemas[0])
    if re.search(r"(?im)^\s*-?\s*Assumption:", manifest):
        raise BundleError("Assumption entries are forbidden; resolve the decision first")
    if re.search(r"(?im)^\s*-?\s*(?:Open question|TBD):", manifest):
        raise BundleError("unresolved questions and TBD entries are forbidden")
    if schema == 4:
        baselines = re.findall(
            r"(?ms)^## Repository baselines\s*\n(.*?)(?=^## |\Z)", manifest
        )
        if len(baselines) != 1 or not re.search(r"(?m)^- \S", baselines[0]):
            raise BundleError(
                "schema 4 PLAN.md requires one non-empty Repository baselines section"
            )
        entries = re.findall(r"(?m)^- (.+)$", baselines[0])
        repository_free = entries == ["None — no repository work."]
        if not repository_free and any(
            "fetched" not in entry.lower()
            or not re.search(r"\b[0-9a-fA-F]{7,64}\b", entry)
            for entry in entries
        ):
            raise BundleError(
                "each Repository baselines entry must name a fetched ref and commit"
            )
        risks = re.findall(
            r"(?ms)^## Risks and resolutions\s*\n(.*?)(?=^## |\Z)", manifest
        )
        if len(risks) != 1 or not re.search(r"(?m)^- \S", risks[0]):
            raise BundleError(
                "schema 4 PLAN.md requires a non-empty Risks and resolutions section"
            )
    block_values = re.findall(r"(?m)^Blocks: (.+)$", manifest)
    if len(block_values) != 1:
        raise BundleError("PLAN.md must contain exactly one Blocks field")
    block_value = block_values[0]
    identifier = TASK_ID.pattern
    segment = rf"(?:{identifier}|\[{identifier}(?:\s*,\s*{identifier})+\])"
    if not re.fullmatch(rf"{segment}(?:\s*>>\s*{segment})*", block_value):
        raise BundleError("Blocks contains invalid syntax")
    block_ids = re.findall(TASK_ID, block_value)
    if len(block_ids) != len(set(block_ids)):
        raise BundleError("Blocks contains duplicate task IDs")
    if set(block_ids) != set(indexed_ids):
        raise BundleError("Blocks and Task index IDs do not match")
    return schema


def validate_skills(value: str, task_id: str) -> None:
    if value == "None":
        return
    skills = [skill.strip() for skill in value.split(",")]
    if not skills or any(not SKILL_NAME.fullmatch(skill) for skill in skills):
        raise BundleError(f"{task_id} contains an invalid Skills list")


def validate_schema_4_fields(content: str, task_id: str) -> None:
    before_results = content.split("\nResults:", 1)[0]
    actual = [name for name, _ in FIELD.findall(before_results)]
    expected = [
        "Status",
        "Model",
        "Skills",
        "Skill context",
        "Goal",
        "Writes",
        "How",
        "Materialization",
        "Handoff",
        "Verification",
    ]
    if "Model reason" in actual:
        expected.insert(2, "Model reason")
    if actual != expected:
        raise BundleError(
            f"{task_id} task fields are missing, unknown, duplicated, or out of order: "
            + ", ".join(actual)
        )


def validate_task_state(content: str, fields: dict[str, str], task_id: str) -> None:
    results = content.split("\nResults:", 1)[1].strip()
    if fields["Status"] == "PENDING" and results:
        raise BundleError(f"{task_id} is PENDING but Results is not empty")
    if fields["Status"] != "PENDING" and not results:
        raise BundleError(f"{task_id} is {fields['Status']} but Results is empty")
    if (
        fields["Status"] == "DONE"
        and fields["Verification"].startswith("Manual")
        and re.search(r"(?i)pending\s+manual", results)
    ):
        raise BundleError(f"{task_id} is DONE with a pending Manual verification")


def validate_tasks(
    files: dict[PurePosixPath, str],
    indexed: dict[PurePosixPath, str],
    schema: int,
) -> None:
    write_owners: dict[str, str] = {}
    required = ["Status", "Model", "Skills", "Goal", "Writes", "How", "Verification", "Results"]
    if schema == 4:
        required[3:3] = ["Skill context"]
        required[6:6] = ["Materialization", "Handoff"]
    for path, task_id in indexed.items():
        content = files[path]
        header_content = content.split("\nResults:", 1)[0] + "\nResults:\n"
        if re.search(r"(?im)^\s*-?\s*Assumption:", content):
            raise BundleError(f"Assumption entries are forbidden in {task_id}")
        if schema == 4:
            validate_schema_4_fields(content, task_id)
        fields = {name: single_field(header_content, name, task_id) for name in required}
        if fields["Status"] not in STATUS:
            raise BundleError(f"invalid Status in {task_id}: {fields['Status']}")
        if fields["Model"] not in {"haiku", "sonnet"}:
            raise BundleError(f"invalid Model in {task_id}: {fields['Model']}")
        reasons = [
            value or ""
            for name, value in FIELD.findall(header_content)
            if name == "Model reason"
        ]
        if schema == 4 and (len(reasons) != 1 or not reasons[0].strip()):
            raise BundleError(f"{task_id} requires one non-empty Model reason")
        if schema < 4:
            if fields["Model"] == "sonnet" and (
                len(reasons) != 1 or not reasons[0].strip()
            ):
                raise BundleError(f"{task_id} requires one non-empty Model reason")
            if fields["Model"] == "haiku" and reasons:
                raise BundleError(f"{task_id} must not contain Model reason for Haiku")
        nonempty = ["Skills", "Goal", "Writes", "How", "Verification"]
        if schema == 4:
            nonempty.extend(["Skill context", "Materialization", "Handoff"])
        if not all(fields[name] for name in nonempty):
            raise BundleError(f"{task_id} contains an empty required field")
        validate_skills(fields["Skills"], task_id)
        if schema == 4:
            if fields["Skills"] == "None" and fields["Skill context"] != "None":
                raise BundleError(
                    f"{task_id} must use Skill context: None when Skills is None"
                )
            if not re.fullmatch(r"None|Local\s+[—-]\s+.+", fields["Materialization"]):
                raise BundleError(f"{task_id} has an invalid Materialization field")
            if (
                fields["Materialization"] != "None"
                and local_verification_is_broad(fields["Materialization"])
                and (
                    "CLAUDE_PLAN_MATERIALIZATION=1" not in fields["Materialization"]
                    or not re.search(
                        r"(?i)-(?:DskipTests|Dmaven\.test\.skip=true)|-x\s+test",
                        fields["Materialization"],
                    )
                )
            ):
                raise BundleError(
                    f"{task_id} broad Materialization must use the explicit marker "
                    "and disable tests"
                )
            validate_task_state(content, fields, task_id)
        verification = fields["Verification"]
        mode = re.match(r"^(CI|Manual|Local)\s+[—-]\s+(.+)$", verification)
        if not mode:
            raise BundleError(f"{task_id} has an invalid Verification mode")
        if mode.group(1) == "Local" and local_verification_is_broad(mode.group(2)):
            raise BundleError(f"{task_id} Local verification is a broad test suite")
        if fields["Writes"] == "None":
            continue
        for raw_path in fields["Writes"].split(","):
            write_path = raw_path.strip()
            if not write_path:
                raise BundleError(f"{task_id} has an empty Writes entry")
            owner = write_owners.setdefault(write_path, task_id)
            if owner != task_id:
                raise BundleError(
                    f"write path {write_path} is owned by both {owner} and {task_id}"
                )


def parse_bundle(text: str) -> tuple[PurePosixPath, dict[PurePosixPath, str]]:
    targets = TARGET.findall(text)
    if len(targets) != 1:
        raise BundleError("bundle must contain exactly one plans/<slug>/ target")
    target = PurePosixPath(targets[0])
    matches = list(FILE_HEADING.finditer(text))
    if not matches:
        raise BundleError("bundle contains no file sections")

    files: dict[PurePosixPath, str] = {}
    for index, match in enumerate(matches):
        relative = safe_relative(match.group(1))
        if relative in files:
            raise BundleError(f"duplicate file section: {relative}")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        files[relative] = parse_section(text[match.end() : end], relative)

    manifest = files.get(PurePosixPath("PLAN.md"))
    if manifest is None:
        raise BundleError("bundle is missing PLAN.md")
    entries = INDEX_ENTRY.findall(manifest)
    indexed_ids = [task_id for task_id, _ in entries]
    if not entries or len(indexed_ids) != len(set(indexed_ids)):
        raise BundleError("Task index is empty or contains duplicate IDs")
    if any(not TASK_ID.fullmatch(task_id) for task_id in indexed_ids):
        raise BundleError("Task index contains an invalid task ID")
    indexed = {PurePosixPath(path): task_id for task_id, path in entries}
    if len(indexed) != len(entries):
        raise BundleError("Task index contains duplicate paths")
    task_files = {path for path in files if path != PurePosixPath("PLAN.md")}
    if set(indexed) != task_files:
        raise BundleError("Task index and staged task files do not match")
    for path, task_id in indexed.items():
        if path.stem != task_id:
            raise BundleError(f"task ID does not match filename: {path}")
        first_line = files[path].splitlines()[0]
        if first_line != f"# {task_id}":
            raise BundleError(f"task heading does not match filename: {path}")
    schema = validate_manifest(manifest, indexed_ids)
    validate_tasks(files, indexed, schema)
    return target, files


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def destination_for(target: PurePosixPath, repo_root: Path) -> Path:
    root = repo_root.expanduser().resolve(strict=True)
    destination = (root / Path(*target.parts)).resolve(strict=False)
    try:
        destination.relative_to(root)
    except ValueError as error:
        raise BundleError("target escapes repository root") from error
    return destination


def validate(staging: Path, repo_root: Path) -> tuple[Path, int]:
    target, files = parse_bundle(staging.read_text(encoding="utf-8"))
    return destination_for(target, repo_root), len(files)


def materialize(staging: Path, repo_root: Path) -> tuple[Path, int]:
    target, files = parse_bundle(staging.read_text(encoding="utf-8"))
    destination = destination_for(target, repo_root)
    for relative, content in files.items():
        output = (destination / Path(*relative.parts)).resolve(strict=False)
        try:
            output.relative_to(destination)
        except ValueError as error:
            raise BundleError(f"output escapes plan directory: {relative}") from error
        atomic_write(output, content)
    return destination, len(files)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("staging", type=Path)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        operation = validate if args.check else materialize
        destination, count = operation(args.staging, args.repo_root)
    except (BundleError, OSError) as error:
        parser.error(str(error))
    verb = "Validated" if args.check else "Materialized"
    print(f"{verb} {count} files for {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
