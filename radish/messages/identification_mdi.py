"""Decoders for Identification MDI payloads (Command Reference section 7.2)."""

from __future__ import annotations


def _decode_ascii_field(raw: bytes) -> str:
    return raw.decode("ascii", errors="replace")


def _parse_null_terminated_ascii(payload: bytes, start: int) -> tuple[str, int, str | None]:
    if start >= len(payload):
        return "", start, "Missing ASCII field (payload ended early)"

    terminator = payload.find(b"\x00", start)
    if terminator == -1:
        return (
            _decode_ascii_field(payload[start:]),
            len(payload),
            "ASCII field missing NULL terminator; consumed remaining payload",
        )

    return _decode_ascii_field(payload[start:terminator]), terminator + 1, None


def _parse_mdy_date(payload: bytes, start: int, label: str) -> tuple[dict[str, object] | None, int, str | None]:
    if start + 3 > len(payload):
        return None, start, f"Incomplete {label} date triplet; expected 3 bytes"

    month = payload[start]
    day = payload[start + 1]
    year = payload[start + 2]
    is_unused = month == 0xFF and day == 0xFF and year == 0xFF
    return (
        {
            "month": month,
            "day": day,
            "year": year,
            "is_unused": is_unused,
        },
        start + 3,
        None,
    )


def _format_date(date_data: dict[str, object] | None) -> str:
    if not date_data:
        return "missing"
    if date_data["is_unused"]:
        return "unused (ff/ff/ff)"
    month = _decode_bcd_byte(int(date_data["month"]))
    day = _decode_bcd_byte(int(date_data["day"]))
    year = _decode_bcd_byte(int(date_data["year"]))
    return f"{month:02d}/{day:02d}/{year:02d}"


def _decode_bcd_byte(value: int) -> int:
    high = (value >> 4) & 0x0F
    low = value & 0x0F
    if high <= 9 and low <= 9:
        return (high * 10) + low
    return value


def decode_get_identification_data(payload: bytes) -> tuple[dict[str, object], list[str]]:
    """Decode Get Identification Data response payload (table 148)."""
    decoded: dict[str, object] = {}
    warnings: list[str] = []

    if len(payload) < 4:
        warnings.append("Identification payload shorter than 4-byte header")
        decoded["raw_payload"] = payload
        return decoded, warnings

    decoded["manufacturer_id"] = int.from_bytes(payload[0:2], "little")
    version_revision = payload[2]
    decoded["ct_version"] = (version_revision >> 4) & 0x0F
    decoded["ct_revision"] = version_revision & 0x0F
    micro_count = payload[3]
    decoded["number_of_micros"] = micro_count

    idx = 4
    micros: list[dict[str, str]] = []
    for micro_idx in range(micro_count):
        sw_version, idx, warning = _parse_null_terminated_ascii(payload, idx)
        if warning:
            warnings.append(f"Micro {micro_idx + 1} SW version: {warning}")

        sw_revision, idx, warning = _parse_null_terminated_ascii(payload, idx)
        if warning:
            warnings.append(f"Micro {micro_idx + 1} SW revision: {warning}")

        serial_number, idx, warning = _parse_null_terminated_ascii(payload, idx)
        if warning:
            warnings.append(f"Micro {micro_idx + 1} serial number: {warning}")

        micros.append(
            {
                "sw_version": sw_version,
                "sw_revision": sw_revision,
                "serial_number": serial_number,
            }
        )
        if idx >= len(payload):
            if micro_idx + 1 < micro_count:
                warnings.append(
                    f"Payload ended while decoding micro list ({micro_idx + 1}/{micro_count} micros decoded)"
                )
            break
    decoded["micros"] = micros

    date_code, idx, warning = _parse_mdy_date(payload, idx, "Date Code")
    if warning:
        warnings.append(warning)
    verification_date, idx, warning = _parse_mdy_date(payload, idx, "Verification/Test")
    if warning:
        warnings.append(warning)
    installation_date, idx, warning = _parse_mdy_date(payload, idx, "Installation")
    if warning:
        warnings.append(warning)
    decoded["date_code"] = date_code
    decoded["verification_date"] = verification_date
    decoded["installation_date"] = installation_date

    trailing_ascii_fields = (
        "address",
        "zip_code",
        "manufacturer",
        "control_name",
        "model",
        "model_version",
        "model_revision",
    )

    if idx >= len(payload):
        for field_name in trailing_ascii_fields:
            decoded[field_name] = "missing"
    else:
        for field_name in trailing_ascii_fields:
            field_value, idx, warning = _parse_null_terminated_ascii(payload, idx)
            decoded[field_name] = field_value
            if warning:
                warnings.append(f"{field_name}: {warning}")

    if idx < len(payload):
        decoded["trailing_bytes"] = payload[idx:]
        warnings.append(
            f"Found {len(payload) - idx} trailing byte(s) after Identification MDI fields"
        )

    decoded["date_code_text"] = _format_date(date_code)
    decoded["verification_date_text"] = _format_date(verification_date)
    decoded["installation_date_text"] = _format_date(installation_date)
    decoded["raw_payload"] = payload
    return decoded, warnings


def decode_set_identification_data(payload: bytes) -> tuple[dict[str, object], list[str]]:
    """Decode Set Identification request payload (table 149)."""
    decoded: dict[str, object] = {}
    warnings: list[str] = []
    idx = 0

    date_code, idx, warning = _parse_mdy_date(payload, idx, "Date Code")
    if warning:
        warnings.append(warning)
    verification_date, idx, warning = _parse_mdy_date(payload, idx, "Verification/Test")
    if warning:
        warnings.append(warning)
    installation_date, idx, warning = _parse_mdy_date(payload, idx, "Installation")
    if warning:
        warnings.append(warning)

    decoded["date_code"] = date_code
    decoded["verification_date"] = verification_date
    decoded["installation_date"] = installation_date

    trailing_ascii_fields = (
        "address",
        "zip_code",
        "manufacturer",
        "control_name",
        "model",
        "model_version",
        "model_revision",
    )
    if idx >= len(payload):
        for field_name in trailing_ascii_fields:
            decoded[field_name] = "missing"
    else:
        for field_name in trailing_ascii_fields:
            field_value, idx, warning = _parse_null_terminated_ascii(payload, idx)
            decoded[field_name] = field_value
            if warning:
                warnings.append(f"{field_name}: {warning}")

    if idx < len(payload):
        decoded["trailing_bytes"] = payload[idx:]
        warnings.append(
            f"Found {len(payload) - idx} trailing byte(s) after Identification MDI fields"
        )

    decoded["date_code_text"] = _format_date(date_code)
    decoded["verification_date_text"] = _format_date(verification_date)
    decoded["installation_date_text"] = _format_date(installation_date)
    decoded["raw_payload"] = payload
    return decoded, warnings
