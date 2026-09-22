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

SYSTEM_ACTIVE_CONTROL_STATUS_MAP = {
    0: "Off",
    1: "Cool State",
    2: "Auto-Cool State",
    3: "Heat State",
    4: "Auto-Heat State",
    5: "Back-Up (Emergency) Heat State",
}

CURTAILMENT_ACTIVE_CONTROL_STATUS_MAP = {
    0: "No Curtailment",
    1: "DLC Curtailment",
    2: "Tiered Price Protection",
    3: "RTP Price Protection",
    4: "Real Time Pricing",
}

DAY_OF_WEEK_MAP = {
    0x00: "Monday",
    0x01: "Tuesday",
    0x02: "Wednesday",
    0x03: "Thursday",
    0x04: "Friday",
    0x05: "Saturday",
    0x06: "Sunday",
    0xFF: "Unknown or Unavailable",
}

THERMOSTAT_FAN_MODE_SETTING_MAP = {
    0: "Auto",
    1: "Always ON",
    2: "ON when occupied (Smart Fan Feature)",
}

MONTH_MAP = {
    0x00: "January",
    0x01: "February",
    0x02: "March",
    0x03: "April",
    0x04: "May",
    0x05: "June",
    0x06: "July",
    0x07: "August",
    0x08: "September",
    0x09: "October",
    0x0A: "November",
    0x0B: "December",
}


def _half_percent(value: int) -> float:
    return value * 0.5


def _mapped(value: int, mapping: dict[int, str], reserved_label: str = "Reserved") -> str:
    name = mapping.get(value, reserved_label)
    return f"{name} ({value})"


def _rh_setpoint_or_reading(value: int) -> str:
    if value == 0:
        return "Not Enabled or Unavailable"
    return f"{value}% RH"


def _clock_byte(value: int, unit: str, max_inclusive: int | None = None) -> str:
    if value == 0xFF:
        return "Unknown or Unavailable"
    if max_inclusive is not None and value > max_inclusive:
        return f"Invalid ({value})"
    return f"{value}{unit}"


def _decode_display_temperature_f(value: bytes) -> str:
    """Decode Table 160 Display Temperature (bytes 7-8).

    Bits 15-12 spare (0), 11-4 whole °F, 3-0 fractional sixteenths.
    """
    raw = int.from_bytes(value, "little")
    whole = (raw >> 4) & 0xFF
    fraction_sixteenths = raw & 0x0F
    temp_f = whole + (fraction_sixteenths / 16.0)
    return f"{temp_f}°F"


def _decode_thermostat_status_db_00(value: bytes) -> dict[str, object]:
    """Decode Table 160 (Thermostat Status Data, DB ID 0x00)."""
    hold_flags = value[15]
    timed_hold = int.from_bytes(value[16:18], "little")
    year = value[25]
    month = value[26]
    date = value[27]
    away = value[29]
    fan_mode = value[30]

    if timed_hold == 0xFFFF:
        timed_hold_text = "Disabled or Unused"
    else:
        timed_hold_text = f"{timed_hold} min"

    if year == 0xFF:
        year_text = "Unknown or Unavailable"
    else:
        year_text = str(2000 + year)

    if month == 0xFF:
        month_text = "Unknown or Unavailable"
    else:
        month_text = _mapped(month, MONTH_MAP, reserved_label="Invalid")

    if date == 0xFF:
        date_text = "Unknown or Unavailable"
    elif 1 <= date <= 31:
        date_text = str(date)
    else:
        date_text = f"Invalid ({date})"

    if away == 0:
        away_text = "Away Mode Disabled or Unavailable (0)"
    elif away == 1:
        away_text = "Away Mode Enabled (1)"
    else:
        away_text = f"Reserved ({away})"

    return {
        "Critical Fault": value[0],
        "Minor Fault": value[1],
        "System Active Control Status": _mapped(
            value[2], SYSTEM_ACTIVE_CONTROL_STATUS_MAP
        ),
        "Curtailment Active Control Status": _mapped(
            value[3], CURTAILMENT_ACTIVE_CONTROL_STATUS_MAP
        ),
        "Humidification Setpoint": _rh_setpoint_or_reading(value[4]),
        "De-humidification Setpoint": _rh_setpoint_or_reading(value[5]),
        "Working Set Point Temperature": f"{value[6]}°F",
        "Display Temperature": _decode_display_temperature_f(value[7:9]),
        "Heat Set Point Temperature": f"{value[9]}°F",
        "Cool Set Point Temperature": f"{value[10]}°F",
        "Current Day of Week": _mapped(value[11], DAY_OF_WEEK_MAP),
        "Current Time - Hours": _clock_byte(value[12], "h", max_inclusive=23),
        "Current Time - Min": _clock_byte(value[13], " min", max_inclusive=59),
        "Current Time - Sec": _clock_byte(value[14], "s", max_inclusive=59),
        "Programmable Hold": "Enabled" if (hold_flags & 0x08) else "Disabled or Unused",
        "Startup Hold": "Enabled" if (hold_flags & 0x04) else "Disabled or Unused",
        "Temporary Hold": "Enabled" if (hold_flags & 0x02) else "Disabled or Unused",
        "Permanent Hold": "Enabled" if (hold_flags & 0x01) else "Disabled or Unused",
        "Timed Temporary Hold Remaining": timed_hold_text,
        "Dehumidification Requested Demand": f"{_half_percent(value[18])}%",
        "Humidification Requested Demand": f"{_half_percent(value[19])}%",
        "Heat Requested Demand": f"{_half_percent(value[20])}%",
        "Cool Requested Demand": f"{_half_percent(value[21])}%",
        "Fan Requested Demand": f"{_half_percent(value[22])}%",
        "Emergency Heat Requested Demand": f"{_half_percent(value[23])}%",
        "Aux Heat Requested Demand": f"{_half_percent(value[24])}%",
        "Current Time - Year": year_text,
        "Current Time - Month": month_text,
        "Current Time - Date": date_text,
        "Relative Humidity Reading": _rh_setpoint_or_reading(value[28]),
        "Away Mode Status": away_text,
        "Fan Mode Setting": _mapped(fan_mode, THERMOSTAT_FAN_MODE_SETTING_MAP),
    }


def _decode_air_handler_status_db_00(value: bytes) -> dict[str, object]:
    """Decode Table 162 (Air Handler Status data, DB ID 0x00)."""
    airflow_cfm = int.from_bytes(value[12:14], "little")
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

    if source_node_type == 1 and db_id == 0x00:
        # Spec Table 160 is 31 bytes; some thermostats answer with an empty
        # record (length 0) to mean no status MDI is published.
        if len(value) == 0:
            return {
                "record_name": "Thermostat Status Data (Table 160)",
                "node_type": source_node_type,
                "node_type_name": NODE_TYPE_MAP[source_node_type],
                "db_id": db_id,
                "raw_value": value,
                "decoded_fields": {
                    "Note": "Empty record — device published no status data",
                },
            }, None
        if len(value) != 31:
            return (
                None,
                f"DB ID 0x00 length mismatch for node type {source_node_type} "
                f"({NODE_TYPE_MAP[source_node_type]}): expected 31, got {len(value)}",
            )
        return {
            "record_name": "Thermostat Status Data (Table 160)",
            "node_type": source_node_type,
            "node_type_name": NODE_TYPE_MAP[source_node_type],
            "db_id": db_id,
            "raw_value": value,
            "decoded_fields": _decode_thermostat_status_db_00(value),
        }, None

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
