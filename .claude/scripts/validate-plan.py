#!/usr/bin/env python3
"""Validate the PLAN.md contract shared by planner and plan-execute."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


TASK_ID_RE = re.compile(r"t[1-9][0-9]*-[a-z0-9]+(?:-[a-z0-9]+)*$")
FIELD_ORDER = [
    "Status",
    "Model",
    "Goal",
    "Writes",
    "How",
    "Verification",
    "Results",
]
STATUSES = {"PENDING", "IN_PROGRESS", "DONE", "FAILED", "BLOCKED"}
MODELS = {"haiku", "sonnet"}
REQUIRED_SECTIONS = [
    "Objective",
    "Boundaries and decisions",
    "Execution order",
    "Tasks",
]
ALLOWED_SECTIONS = set(REQUIRED_SECTIONS) | {"Grounded facts", "Manual actions"}
OBSOLETE_FIELDS_RE = re.compile(r"^(Why|Evidence|Dependencies|Context):", re.MULTILINE)
PLACEHOLDER_RE = re.compile(r"<[^>\n]+>|\b(?:TODO|TBD|PLACEHOLDER)\b", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--phase", choices=("planning", "execution"), required=True)
    return parser.parse_args()


def section_map(lines: list[str], errors: list[str]) -> tuple[dict[str, tuple[int, int]], list[str]]:
    headings: list[tuple[str, int]] = []
    for index, line in enumerate(lines):
        match = re.fullmatch(r"## ([^#].*)", line)
        if match:
            headings.append((match.group(1).strip(), index))

    sections: dict[str, tuple[int, int]] = {}
    order: list[str] = []
    for position, (name, start) in enumerate(headings):
        end = headings[position + 1][1] if position + 1 < len(headings) else len(lines)
        if name in sections:
            errors.append(f"duplicate section: {name}")
            continue
        sections[name] = (start + 1, end)
        order.append(name)

    for name in order:
        if name not in ALLOWED_SECTIONS:
            errors.append(f"unsupported section: {name}")
    for name in REQUIRED_SECTIONS:
        if name not in sections:
            errors.append(f"missing section: {name}")

    if all(name in sections for name in REQUIRED_SECTIONS):
        positions = [order.index(name) for name in REQUIRED_SECTIONS]
        if positions != sorted(positions):
            errors.append("required sections are out of order")
        grounded = order.index("Grounded facts") if "Grounded facts" in order else None
        if grounded is not None and not (
            order.index("Boundaries and decisions") < grounded < order.index("Execution order")
        ):
            errors.append("Grounded facts must appear between Boundaries and decisions and Execution order")
        manual = order.index("Manual actions") if "Manual actions" in order else None
        if manual is not None and manual < order.index("Tasks"):
            errors.append("Manual actions must appear after Tasks")

    return sections, order


def section_content(lines: list[str], sections: dict[str, tuple[int, int]], name: str) -> str:
    if name not in sections:
        return ""
    start, end = sections[name]
    return "\n".join(lines[start:end]).strip()


def parse_blocks(value: str, errors: list[str]) -> list[list[str]]:
    groups: list[list[str]] = []
    if not value.strip():
        errors.append("Blocks value is empty")
        return groups

    for raw_group in value.split(">>"):
        raw_group = raw_group.strip()
        if raw_group.startswith("[") or raw_group.endswith("]"):
            if not (raw_group.startswith("[") and raw_group.endswith("]")):
                errors.append(f"malformed parallel block: {raw_group}")
                continue
            ids = [item.strip() for item in raw_group[1:-1].split(",") if item.strip()]
            if len(ids) < 2:
                errors.append(f"parallel block must contain at least two tasks: {raw_group}")
        else:
            ids = [raw_group]

        for task_id in ids:
            if not TASK_ID_RE.fullmatch(task_id):
                errors.append(f"invalid task ID in Blocks: {task_id}")
        groups.append(ids)

    flattened = [task_id for group in groups for task_id in group]
    duplicates = sorted({task_id for task_id in flattened if flattened.count(task_id) > 1})
    if duplicates:
        errors.append(f"duplicate task IDs in Blocks: {', '.join(duplicates)}")
    return groups


def field_value(
    body: list[str],
    positions: dict[str, int],
    field: str,
) -> tuple[str, list[str]]:
    start = positions[field]
    next_positions = [position for position in positions.values() if position > start]
    end = min(next_positions) if next_positions else len(body)
    inline = body[start].split(":", 1)[1].strip()
    continuation = body[start + 1 : end]
    content = "\n".join(([inline] if inline else []) + continuation).strip()
    return content, continuation


def parse_tasks(
    lines: list[str],
    sections: dict[str, tuple[int, int]],
    phase: str,
    errors: list[str],
) -> tuple[list[str], dict[str, list[str]]]:
    if "Tasks" not in sections:
        return [], {}

    start, end = sections["Tasks"]
    task_headings: list[tuple[str, int]] = []
    for index in range(start, end):
        match = re.fullmatch(r"### (.+)", lines[index])
        if match:
            task_headings.append((match.group(1).strip(), index))

    if not task_headings:
        errors.append("Tasks section contains no tasks")
        return [], {}

    task_ids: list[str] = []
    writes_by_task: dict[str, list[str]] = {}
    for position, (task_id, heading_line) in enumerate(task_headings):
        task_end = task_headings[position + 1][1] if position + 1 < len(task_headings) else end
        body = lines[heading_line + 1 : task_end]
        task_ids.append(task_id)

        if not TASK_ID_RE.fullmatch(task_id):
            errors.append(f"invalid task heading ID: {task_id}")
        occurrences: dict[str, list[int]] = {field: [] for field in FIELD_ORDER}
        results_lines = [
            body_index
            for body_index, line in enumerate(body)
            if re.match(r"^Results:", line)
        ]
        occurrences["Results"] = results_lines
        field_scan_end = results_lines[0] if results_lines else len(body)
        if OBSOLETE_FIELDS_RE.search("\n".join(body[:field_scan_end])):
            errors.append(f"{task_id}: contains an obsolete task field")
        for body_index, line in enumerate(body[:field_scan_end]):
            for field in FIELD_ORDER[:-1]:
                if re.match(rf"^{re.escape(field)}:", line):
                    occurrences[field].append(body_index)

        missing_or_duplicate = False
        positions: dict[str, int] = {}
        for field in FIELD_ORDER:
            count = len(occurrences[field])
            if count == 0:
                errors.append(f"{task_id}: missing field {field}")
                missing_or_duplicate = True
            elif count > 1:
                errors.append(f"{task_id}: duplicate field {field}")
                missing_or_duplicate = True
            else:
                positions[field] = occurrences[field][0]
        if missing_or_duplicate:
            continue

        ordered_positions = [positions[field] for field in FIELD_ORDER]
        if ordered_positions != sorted(ordered_positions):
            errors.append(f"{task_id}: fields are out of order")
        if any(line.strip() for line in body[: positions["Status"]]):
            errors.append(f"{task_id}: unexpected content before Status")

        values: dict[str, str] = {}
        continuations: dict[str, list[str]] = {}
        for field in FIELD_ORDER:
            values[field], continuations[field] = field_value(body, positions, field)

        for field in ("Status", "Model", "Goal", "Writes"):
            if any(line.strip() for line in continuations[field]):
                errors.append(f"{task_id}: {field} must be a single line")
        for field in ("Status", "Model", "Goal", "Writes", "How", "Verification"):
            if not values[field]:
                errors.append(f"{task_id}: {field} is empty")

        status = values["Status"]
        model = values["Model"]
        if status not in STATUSES:
            errors.append(f"{task_id}: invalid Status {status!r}")
        if model not in MODELS:
            errors.append(f"{task_id}: invalid Model {model!r}")

        results = values["Results"]
        if phase == "planning":
            if status != "PENDING":
                errors.append(f"{task_id}: planning Status must be PENDING")
            if results:
                errors.append(f"{task_id}: planning Results must be empty")
        else:
            if status in {"DONE", "FAILED", "BLOCKED"} and not results:
                errors.append(f"{task_id}: {status} requires non-empty Results")
            if status == "PENDING" and results:
                errors.append(f"{task_id}: PENDING Results must be empty")

        writes = values["Writes"]
        if writes.lower() == "none":
            writes_by_task[task_id] = []
        else:
            parsed_writes = [item.strip() for item in writes.split(",") if item.strip()]
            if not parsed_writes:
                errors.append(f"{task_id}: Writes must be comma-separated paths/globs or None")
            duplicates = sorted({item for item in parsed_writes if parsed_writes.count(item) > 1})
            if duplicates:
                errors.append(f"{task_id}: duplicate Writes entries: {', '.join(duplicates)}")
            writes_by_task[task_id] = parsed_writes

    duplicate_headings = sorted({task_id for task_id in task_ids if task_ids.count(task_id) > 1})
    if duplicate_headings:
        errors.append(f"duplicate task headings: {', '.join(duplicate_headings)}")
    return task_ids, writes_by_task


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    try:
        text = args.plan.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read {args.plan}: {exc}", file=sys.stderr)
        return 1

    lines = text.splitlines()
    h1 = [line for line in lines if re.fullmatch(r"# [^#].+", line)]
    if len(h1) != 1:
        errors.append("plan must contain exactly one level-1 title")
    if text.count("Plan schema: 1") != 1:
        errors.append("plan must contain exactly one 'Plan schema: 1' line")
    placeholder = PLACEHOLDER_RE.search(text)
    if placeholder:
        errors.append(f"unresolved placeholder: {placeholder.group(0)}")

    sections, _ = section_map(lines, errors)
    for name in ("Objective", "Boundaries and decisions"):
        if name in sections and not section_content(lines, sections, name):
            errors.append(f"section is empty: {name}")
    for name in ("Grounded facts", "Manual actions"):
        if name in sections and not section_content(lines, sections, name):
            errors.append(f"optional section must be omitted when empty: {name}")

    groups: list[list[str]] = []
    if "Execution order" in sections:
        execution_text = section_content(lines, sections, "Execution order")
        block_lines = re.findall(r"^Blocks:\s*(.*)$", execution_text, re.MULTILINE)
        if len(block_lines) != 1:
            errors.append("Execution order must contain exactly one Blocks line")
        else:
            groups = parse_blocks(block_lines[0], errors)

    task_ids, writes_by_task = parse_tasks(lines, sections, args.phase, errors)
    block_ids = [task_id for group in groups for task_id in group]
    if groups and task_ids:
        if block_ids != task_ids:
            missing = [task_id for task_id in task_ids if task_id not in block_ids]
            unknown = [task_id for task_id in block_ids if task_id not in task_ids]
            if missing:
                errors.append(f"tasks missing from Blocks: {', '.join(missing)}")
            if unknown:
                errors.append(f"Blocks references unknown tasks: {', '.join(unknown)}")
            if not missing and not unknown:
                errors.append("task heading order must match flattened Blocks order")

        for group in groups:
            owners: dict[str, str] = {}
            for task_id in group:
                for path in writes_by_task.get(task_id, []):
                    if path in owners:
                        errors.append(
                            f"parallel write conflict on {path}: {owners[path]} and {task_id}"
                        )
                    else:
                        owners[path] = task_id

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        f"OK: {args.plan} ({len(task_ids)} tasks, {len(groups)} blocks, {args.phase})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
