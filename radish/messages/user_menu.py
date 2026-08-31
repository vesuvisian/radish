"""Helpers for decoding ClimateTalk user menu payloads."""

from __future__ import annotations

from typing import Any


TOKEN_MENU_TITLE_START = 0xB6
TOKEN_MENU_TITLE_END = 0xB7
TOKEN_ITEM_START = 0xC2
TOKEN_ITEM_END = 0xC3
TOKEN_ITEM_LABEL = 0xE1
TOKEN_ITEM_LABEL_ALT = 0xE2
TOKEN_OPTION = 0xE0
TOKEN_OPTION_SELECTED = 0xE8


def _decode_ascii(value: bytes) -> str:
    return value.decode("ascii", errors="replace").strip()


def _is_empty_item(label: str, options: list[str]) -> bool:
    """Return True for parser-noise items with no useful content."""
    if label.strip():
        return False
    if not options:
        return True
    return all(not option.strip() for option in options)


def _read_until_token(payload: bytes, offset: int, stop_tokens: set[int]) -> tuple[bytes, int]:
    i = offset
    while i < len(payload) and payload[i] not in stop_tokens:
        i += 1
    return payload[offset:i], i


def decode_user_menu_payload(payload: bytes) -> dict[str, Any]:
    """Decode menu payload body (after first 6 header bytes)."""
    result: dict[str, Any] = {"title": None, "items": [], "directory_entries": [], "warnings": []}
    i = 0

    if i < len(payload) and payload[i] == TOKEN_MENU_TITLE_START:
        i += 1
        title_raw, i = _read_until_token(payload, i, {TOKEN_MENU_TITLE_END})
        result["title"] = _decode_ascii(title_raw)
        if i < len(payload) and payload[i] == TOKEN_MENU_TITLE_END:
            i += 1
        else:
            result["warnings"].append("Menu title start token found without title end token")

    # Parse directory-entry style payloads (repeated b6...b7 blocks),
    # which may begin after non-menu prefix bytes (e.g., a0:a6).
    scan_i = 0
    while scan_i < len(payload):
        if payload[scan_i] != TOKEN_MENU_TITLE_START:
            scan_i += 1
            continue
        scan_i += 1
        entry_raw, scan_i = _read_until_token(payload, scan_i, {TOKEN_MENU_TITLE_END})
        if scan_i < len(payload) and payload[scan_i] == TOKEN_MENU_TITLE_END:
            scan_i += 1
            entry = _decode_ascii(entry_raw)
            if entry:
                result["directory_entries"].append(entry)
        else:
            result["warnings"].append("Directory title token found without title end token")
            break

    while i < len(payload):
        # Skip noisy repeated item-end delimiters between items (e.g. c3:c3:c2).
        if payload[i] == TOKEN_ITEM_END:
            i += 1
            continue

        if payload[i] != TOKEN_ITEM_START:
            i += 1
            continue

        i += 1
        label = ""
        options: list[str] = []
        selected_index: int | None = None

        if i < len(payload) and payload[i] in {TOKEN_ITEM_LABEL, TOKEN_ITEM_LABEL_ALT}:
            i += 1
            label_raw, i = _read_until_token(
                payload,
                i,
                {TOKEN_OPTION, TOKEN_OPTION_SELECTED, TOKEN_ITEM_END, TOKEN_ITEM_START},
            )
            label = _decode_ascii(label_raw)

        while i < len(payload) and payload[i] in {TOKEN_OPTION, TOKEN_OPTION_SELECTED}:
            is_selected = payload[i] == TOKEN_OPTION_SELECTED
            i += 1
            option_raw, i = _read_until_token(
                payload,
                i,
                {TOKEN_OPTION, TOKEN_OPTION_SELECTED, TOKEN_ITEM_END, TOKEN_ITEM_START},
            )
            option = _decode_ascii(option_raw)
            options.append(option)
            if is_selected:
                selected_index = len(options) - 1

        if i < len(payload) and payload[i] == TOKEN_ITEM_END:
            i += 1
        elif i < len(payload) and payload[i] == TOKEN_ITEM_START:
            # Some payloads omit c3 before the next c2; treat it as implicit termination.
            pass
        else:
            result["warnings"].append(f"Menu item '{label}' missing item-end token")

        selected_option = None
        if selected_index is not None and selected_index < len(options):
            selected_option = options[selected_index]

        if not _is_empty_item(label, options):
            result["items"].append(
                {
                    "label": label,
                    "options": options,
                    "selected_index": selected_index,
                    "selected_option": selected_option,
                }
            )

    return result
