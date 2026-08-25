"""Apply optimization decisions to live resume content."""

from __future__ import annotations

import copy
import re
from typing import Any, Literal

from app.core.exceptions import AppError

DecisionAction = Literal["accept", "reject"]

FIELD_PATH_RE = re.compile(r"^(?P<section>\w+)(?:\[(?P<index>\d+)\])?(?:\.(?P<field>\w+))?$")


def make_change_id(change: dict[str, Any]) -> str:
    if change.get("change_id"):
        return str(change["change_id"])
    field_path = change.get("field_path") or change.get("section") or "unknown"
    return str(field_path)


def attach_change_ids(changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, int] = {}
    enriched: list[dict[str, Any]] = []
    for change in changes:
        item = dict(change)
        base_id = make_change_id(item)
        count = seen.get(base_id, 0)
        seen[base_id] = count + 1
        item["change_id"] = base_id if count == 0 else f"{base_id}#{count + 1}"
        enriched.append(item)
    return enriched


def get_value_at_path(structure: dict[str, Any], field_path: str) -> Any:
    match = FIELD_PATH_RE.match(field_path)
    if not match:
        return structure.get(field_path)

    section = match.group("section")
    index = match.group("index")
    field = match.group("field")

    if index is None:
        return structure.get(section)

    entries = structure.get(section) or []
    entry_index = int(index)
    if entry_index >= len(entries):
        return None
    entry = entries[entry_index]
    if field is None:
        return entry
    if isinstance(entry, dict):
        return entry.get(field)
    return None


def set_value_at_path(structure: dict[str, Any], field_path: str, value: Any) -> None:
    match = FIELD_PATH_RE.match(field_path)
    if not match:
        structure[field_path] = value
        return

    section = match.group("section")
    index = match.group("index")
    field = match.group("field")

    if index is None:
        structure[section] = value
        return

    entries = list(structure.get(section) or [])
    entry_index = int(index)
    if entry_index >= len(entries):
        raise AppError(
            f"Cannot apply change — path not found: {field_path}",
            code="change_path_not_found",
            status_code=422,
        )

    entry = dict(entries[entry_index]) if isinstance(entries[entry_index], dict) else {}
    if field is None:
        entries[entry_index] = value
    else:
        entry[field] = value
        entries[entry_index] = entry
    structure[section] = entries


def apply_optimization_decisions(
    *,
    current_content: dict[str, Any],
    original_content: dict[str, Any],
    optimized_content: dict[str, Any],
    changes: list[dict[str, Any]],
    decisions: list[dict[str, str]],
) -> tuple[dict[str, Any], list[str]]:
    """Return updated content and list of accepted change_ids."""
    change_map = {change["change_id"]: change for change in changes if change.get("change_id")}
    updated = copy.deepcopy(current_content)
    accepted_ids: list[str] = []

    for decision in decisions:
        change_id = decision["change_id"]
        action = decision["action"]
        if action == "reject":
            continue
        if action != "accept":
            raise AppError(
                f"Unsupported decision action: {action}",
                code="invalid_decision_action",
                status_code=422,
            )

        change = change_map.get(change_id)
        if change is None:
            raise AppError(
                f"Unknown change_id: {change_id}",
                code="change_not_found",
                status_code=404,
            )

        field_path = change.get("field_path") or change.get("section")
        if not field_path:
            raise AppError(
                "Change is missing a field path.",
                code="change_path_missing",
                status_code=422,
            )

        optimized_value = get_value_at_path(optimized_content, field_path)
        if optimized_value is None and field_path not in optimized_content:
            optimized_value = optimized_content.get(change.get("section", ""))

        set_value_at_path(updated, field_path, optimized_value)
        accepted_ids.append(change_id)

    if original_content.get("_meta"):
        meta = dict(updated.get("_meta") or original_content["_meta"])
        updated["_meta"] = meta

    return updated, accepted_ids


def build_bulk_decisions(
    changes: list[dict[str, Any]],
    *,
    action: DecisionAction,
) -> list[dict[str, str]]:
    return [{"change_id": change["change_id"], "action": action} for change in changes]
