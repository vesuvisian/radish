"""Node-type-aware Status MDI decoding helpers."""

from __future__ import annotations

from ..maps import NODE_TYPE_MAP

FAN_DEMAND_MODE_MAP = {
    0: "Manual",
    1: "Cool",
    2: "Heat",
    3: "Aux Heat",
    4: "Emer Heat",
    5: "Defrost",
}


def _half_percent(value: int) -> float:
    return value * 0.5


def _decode_air_handler_status_db_00(value: bytes) -> dict[str, object]:
    """Decode Table 162 (Air Handler Status data, DB ID 0x00)."""
    airflow_cfm = int.from_bytes(value[12:14], "big")
    fan_mode = value[3]
    fan_mode_name = FAN_DEMAND_MODE_MAP.get(fan_mode, "Unknown")
    return {
        "Critical Fault": value[0],
        "Minor Fault": value[1],
        "Heat Requested Demand": f"{_half_percent(value[2])}%",
        "Fan Requested Mode": f"{fan_mode_name} ({fan_mode})",
        "Fan Requested Demand": f"{_half_percent(value[4])}%",
        "Fan Requested Rate/Slew": f"{value[5]}s",
        "Fan Requested Delay": f"{value[6]}s",
        "Defrost Requested Demand": f"{_half_percent(value[7])}%",
        "Emergency Requested Demand": f"{_half_percent(value[8])}%",
        "Aux Requested Demand": f"{_half_percent(value[9])}%",
        "Humidification Requested Demand": f"{_half_percent(value[10])}%",
        "Dehumidification Requested Demand": f"{_half_percent(value[11])}%",
        "Current Airflow": f"{airflow_cfm} CFM",
        "Current Heat Actual Status": f"{_half_percent(value[14])}%",
        "Current Fan Actual Status": f"{_half_percent(value[15])}%",
        "Fan Current Rate Status": f"{value[16]}s",
        "Fan Current Delay Remaining Status": f"{value[17]}s",
        "Current Humidification Actual Status": f"{_half_percent(value[18])}%",
        "Current Dehumidification Actual Status": f"{_half_percent(value[19])}%",
    }


def _decode_heat_pump_status_db_00(value: bytes) -> dict[str, object]:
    """Decode Heat Pump Status data (DB ID 0x00)."""
    return {
        "Critical Fault": value[0],
        "Minor Fault": value[1],
        "Heat Requested Demand": f"{_half_percent(value[2])}%",
        "Cool Requested Demand": f"{_half_percent(value[3])}%",
        "Dehumidification Requested Demand": f"{_half_percent(value[4])}%",
        "Heat Current Demand Status": f"{_half_percent(value[5])}%",
        "Cool Current Demand Status": f"{_half_percent(value[6])}%",
        "Defrost Requested Demand": f"{_half_percent(value[7])}%",
        "Fan Requested Demand": f"{_half_percent(value[8])}%",
        "Fan Requested Rate/Slew": f"{value[9]}s",
        "Fan Requested Delay": f"{value[10]}s",
        "Current Dehumidification Actual Status": f"{_half_percent(value[11])}%",
    }


def decode_status_mdi_record(
    source_node_type: int | None, db_id: int, value: bytes
) -> tuple[dict[str, object] | None, str | None]:
    """Decode one Status MDI DB-ID record using source node type."""
    if source_node_type is None:
        return None, "Cannot decode status DB IDs without source node type context"

    if source_node_type == 3 and db_id == 0x00:
        if len(value) != 20:
            return (
                None,
                f"DB ID 0x00 length mismatch for node type {source_node_type} "
                f"({NODE_TYPE_MAP[source_node_type]}): expected 20, got {len(value)}",
            )
        return {
            "record_name": "Air Handler Status Data (Table 162)",
            "node_type": source_node_type,
            "node_type_name": NODE_TYPE_MAP[source_node_type],
            "db_id": db_id,
            "raw_value": value,
            "decoded_fields": _decode_air_handler_status_db_00(value),
        }, None

    if source_node_type == 5 and db_id == 0x00:
        if len(value) != 12:
            return (
                None,
                f"DB ID 0x00 length mismatch for node type {source_node_type} "
                f"({NODE_TYPE_MAP[source_node_type]}): expected 12, got {len(value)}",
            )
        return {
            "record_name": "Heat Pump Status Data",
            "node_type": source_node_type,
            "node_type_name": NODE_TYPE_MAP[source_node_type],
            "db_id": db_id,
            "raw_value": value,
            "decoded_fields": _decode_heat_pump_status_db_00(value),
        }, None

    return (
        None,
        f"No Status MDI definition for node type {source_node_type} "
        f"({NODE_TYPE_MAP[source_node_type]}), DB ID 0x{db_id:02x}",
    )
