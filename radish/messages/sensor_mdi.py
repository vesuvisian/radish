"""Node-type-aware Sensor MDI decoding helpers."""

from __future__ import annotations

from typing import Callable

from ..maps import NODE_TYPE_MAP

SensorDecoder = Callable[[bytes], dict[str, object]]


def _decode_packed_temp_f(value: bytes) -> dict[str, object]:
    """Decode 16-bit packed temperature: valid/sign/whole/fraction."""
    # Command Reference bitfield tables are interpreted in little-endian byte order.
    raw = int.from_bytes(value, "little")
    is_valid = bool((raw >> 15) & 0x01)
    is_negative = bool((raw >> 14) & 0x01)
    whole = (raw >> 4) & 0x03FF
    fraction_sixteenths = raw & 0x0F
    magnitude_f = whole + (fraction_sixteenths / 16.0)
    temp_f = -magnitude_f if is_negative else magnitude_f
    return {
        "valid": is_valid,
        "sign": "negative" if is_negative else "positive",
        "whole": whole,
        "fraction_sixteenths": fraction_sixteenths,
        "value_f": temp_f,
        "units": "degF",
    }


def _decode_packed_relative_humidity(value: bytes) -> dict[str, object]:
    """Decode 16-bit packed RH: valid/reserved/whole/fraction."""
    # Command Reference bitfield tables are interpreted in little-endian byte order.
    raw = int.from_bytes(value, "little")
    is_valid = bool((raw >> 15) & 0x01)
    reserved_bit = bool((raw >> 14) & 0x01)
    whole = (raw >> 4) & 0x03FF
    fraction_sixteenths = raw & 0x0F
    rh = whole + (fraction_sixteenths / 16.0)
    return {
        "valid": is_valid,
        "reserved_bit_14": reserved_bit,
        "whole": whole,
        "fraction_sixteenths": fraction_sixteenths,
        "value_percent": rh,
        "units": "percent_rh",
    }


def _entry(name: str, expected_length: int, decoder: SensorDecoder) -> dict[str, object]:
    return {
        "name": name,
        "expected_length": expected_length,
        "decoder": decoder,
    }


# Section 7.5 mappings from ClimateTalk 2.0 Command Reference.
SENSOR_MDI_SPECS_BY_NODE_TYPE: dict[int, dict[int, dict[str, object]]] = {
    2: {  # Gas Furnace
        0: _entry("Return Air Temperature Sensor", 2, _decode_packed_temp_f),
        1: _entry("Supply Air Temperature Sensor", 2, _decode_packed_temp_f),
    },
    3: {  # Air Handler
        0: _entry("Return Air Temperature Sensor", 2, _decode_packed_temp_f),
        1: _entry("Supply Air Temperature Sensor", 2, _decode_packed_temp_f),
    },
    4: {  # Air Conditioner
        0: _entry("Outdoor Temperature Sensor", 2, _decode_packed_temp_f),
    },
    5: {  # Heat Pump
        0: _entry("Outdoor Temperature Sensor", 2, _decode_packed_temp_f),
    },
    9: {  # Crossover
        0: _entry("Outdoor Temperature Sensor", 2, _decode_packed_temp_f),
        1: _entry("Return Air Temperature Sensor", 2, _decode_packed_temp_f),
        2: _entry("Supply Air Temperature Sensor", 2, _decode_packed_temp_f),
    },
    22: {  # Zone User Interface
        0: _entry("Local Temperature Sensor", 2, _decode_packed_temp_f),
        1: _entry("Relative Humidity Sensor", 2, _decode_packed_relative_humidity),
    },
    38: {  # Zone Temperature Control
        0: _entry("Local Temperature Sensor", 2, _decode_packed_temp_f),
        1: _entry("Relative Humidity Sensor", 2, _decode_packed_relative_humidity),
    },
    # Standalone temperature-style sensors (sections 7.5.8 - 7.5.11):
    # SAT, RAT, OAT, Remote Temperature.
    39: {  # Temperature Sensor
        0: _entry("Remote Temperature Sensor", 2, _decode_packed_temp_f),
    },
}


def decode_sensor_mdi_record(
    source_node_type: int | None, db_id: int, value: bytes
) -> tuple[dict[str, object] | None, str | None]:
    """Decode one Sensor MDI DB-ID record using source node type."""
    if source_node_type is None:
        return None, "Cannot decode sensor DB IDs without source node type context"

    specs = SENSOR_MDI_SPECS_BY_NODE_TYPE.get(source_node_type)
    if not specs:
        return (
            None,
            f"No Sensor MDI map for source node type {source_node_type} "
            f"({NODE_TYPE_MAP[source_node_type]})",
        )

    spec = specs.get(db_id)
    if not spec:
        return (
            None,
            f"No Sensor MDI definition for node type {source_node_type} "
            f"({NODE_TYPE_MAP[source_node_type]}), DB ID 0x{db_id:02x}",
        )

    expected_length = spec["expected_length"]
    if len(value) != expected_length:
        return (
            None,
            f"DB ID 0x{db_id:02x} length mismatch for node type {source_node_type} "
            f"({NODE_TYPE_MAP[source_node_type]}): expected {expected_length}, got {len(value)}",
        )

    decoded_fields = spec["decoder"](value)
    decoded = {
        "sensor_name": spec["name"],
        "node_type": source_node_type,
        "node_type_name": NODE_TYPE_MAP[source_node_type],
        "db_id": db_id,
        "raw_value": value,
        "decoded_fields": decoded_fields,
    }
    return decoded, None


def decode_sensor_mdi_potential_values(
    source_node_type: int | None, db_id: int, value: bytes
) -> list[dict[str, object]]:
    """Return experimental candidate decodings for unknown vendor-specific records."""
    # Air Handler DB ID 0x02 appears to be a 20-byte vendor sensor block.
    if source_node_type != 3 or db_id != 0x02 or len(value) != 20:
        return []

    words: list[dict[str, object]] = []
    slot_name_map = {
        0: "Liquid Temperature",
        1: "Suction Temperature",
        6: "Pressure Sensor (tentative)",
    }

    for idx in range(0, len(value), 2):
        word_bytes = value[idx : idx + 2]
        slot = idx // 2
        raw_le = int.from_bytes(word_bytes, "little")
        signed_le = int.from_bytes(word_bytes, "little", signed=True)

        packed_temp = _decode_packed_temp_f(word_bytes)
        preferred_value = None
        preferred_units = None
        if slot in slot_name_map:
            if slot in {0, 1} and packed_temp["valid"]:
                preferred_value = packed_temp["value_f"]
                preferred_units = "degF"
            elif slot == 6:
                is_valid = bool(raw_le & 0x8000)
                if is_valid:
                    # Tentative model: bit15 validity flag, remaining 15 bits are PSI.
                    preferred_value = raw_le & 0x7FFF
                    preferred_units = "PSI"
                else:
                    preferred_value = None
                    preferred_units = "invalid"
            else:
                preferred_value = None
                preferred_units = "invalid"

        words.append(
            {
                "slot": slot,
                "slot_name": slot_name_map.get(slot),
                "bytes": word_bytes.hex(":"),
                "u16_le": raw_le,
                "s16_le": signed_le,
                "u16_div10": raw_le / 10.0,
                "s16_div10": signed_le / 10.0,
                "packed_valid": packed_temp["valid"],
                "packed_value_f": packed_temp["value_f"],
                "preferred_value": preferred_value,
                "preferred_units": preferred_units,
            }
        )

    return words
