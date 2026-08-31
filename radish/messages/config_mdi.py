"""Node-type-aware Configuration MDI decoding helpers."""

from __future__ import annotations

from ..maps import NODE_TYPE_MAP


def _decode_modulating_count(raw_value: int) -> str:
    """Decode stage/speed count nibble with 0xF as variable/modulating."""
    if raw_value == 0x0F:
        return "Variable/Modulating"
    return str(raw_value)


def _decode_hvac_operation(value: int) -> str:
    return {
        0x00: "24VAC",
        0x01: "Serial",
        0x02: "Combo Operation",
        0x03: "Reserved",
    }[value & 0x03]


def _decode_furnace_hvac_operation(value: int) -> str:
    return {
        0x00: "24VAC",
        0x01: "Serial",
        0x02: "Combo Operation",
        0x03: "Water",
    }[value & 0x03]


def _decode_furnace_configuration_db_00(value: bytes) -> dict[str, object]:
    """Decode Furnace Configuration Data (Table 153, DB ID 0x00)."""
    fan_speeds_raw = (value[0] >> 4) & 0x0F
    inducer_stages_raw = value[0] & 0x0F
    heat_stages_raw = (value[1] >> 4) & 0x0F
    cool_stages_raw = value[1] & 0x0F
    config_bits = value[2]
    capability_flags = value[3]
    # Table 153 encodes this 16-bit airflow value little-endian.
    max_airflow_cfm = int.from_bytes(value[7:9], "little")

    pressure_config = {
        0x00: "Sensorless",
        0x01: "Pressure Switch",
        0x02: "Transducer",
        0x03: "Reserved",
    }[(config_bits >> 6) & 0x03]
    ignition_type = {
        0x00: "Spark",
        0x01: "Silicon Carbide",
        0x02: "Silicon Nitride",
        0x03: "Reserved",
    }[(config_bits >> 4) & 0x03]
    fuel_type = {
        0x00: "Propane",
        0x01: "Natural",
        0x02: "Reserved",
        0x03: "Reserved",
    }[(config_bits >> 2) & 0x03]

    return {
        "Fan Speeds": _decode_modulating_count(fan_speeds_raw),
        "Inducer Stages": _decode_modulating_count(inducer_stages_raw),
        "Heat Stages": _decode_modulating_count(heat_stages_raw),
        "Cool Stages": _decode_modulating_count(cool_stages_raw),
        "Pressure Configuration": pressure_config,
        "Ignition Type": ignition_type,
        "Fuel Type": fuel_type,
        "HVAC Operation": _decode_furnace_hvac_operation(config_bits),
        "Humidification Capable in Cool Mode": "Yes"
        if (capability_flags & 0x04)
        else "No",
        "Humidification Capable": "Yes" if (capability_flags & 0x02) else "No",
        "Dehumidification Capable": "Yes" if (capability_flags & 0x01) else "No",
        "Furnace Size": f"{value[4]} kBTU" if value[4] != 0 else "Unavailable",
        "Circulator/Blower Motor Manufacturer": value[5],
        "Circulator/Blower Motor Size": _decode_fan_motor_size_hp(value[6]),
        "Circulator/Blower Maximum Airflow": f"{max_airflow_cfm} CFM",
    }


def _decode_heat_pump_configuration_db_00(value: bytes) -> dict[str, object]:
    """Decode Heat Pump Configuration Data (Table 156, DB ID 0x00)."""
    operation_flags = value[2]
    capability_flags = value[3]
    nominal_capacity_tons = value[4] / 2.0
    fan_speeds_raw = (value[0] >> 4) & 0x0F
    heat_stages_raw = (value[1] >> 4) & 0x0F
    cool_stages_raw = value[1] & 0x0F
    return {
        "Fan Speeds": _decode_modulating_count(fan_speeds_raw),
        "Heat Stages": _decode_modulating_count(heat_stages_raw),
        "Cool Stages": _decode_modulating_count(cool_stages_raw),
        "HVAC Operation": _decode_hvac_operation(operation_flags),
        "Dehumidification Capable": "Yes" if (capability_flags & 0x01) else "No",
        "Nominal Capacity": f"{nominal_capacity_tons:g} tons",
    }


def _decode_air_conditioner_configuration_db_00(value: bytes) -> dict[str, object]:
    """Decode Air Conditioner Configuration Data (Table 155, DB ID 0x00)."""
    operation_flags = value[2]
    capability_flags = value[3]
    nominal_capacity_tons = value[4] / 2.0
    outdoor_fan_speeds_raw = (value[0] >> 4) & 0x0F
    cool_stages_raw = value[1] & 0x0F
    return {
        "Outdoor Fan Speeds": _decode_modulating_count(outdoor_fan_speeds_raw),
        "Cool Stages": _decode_modulating_count(cool_stages_raw),
        "HVAC Operation": _decode_hvac_operation(operation_flags),
        "Dehumidification Capable": "Yes" if (capability_flags & 0x01) else "No",
        "Nominal Capacity": f"{nominal_capacity_tons:g} tons",
    }


def _decode_air_handler_configuration_db_00(value: bytes) -> dict[str, object]:
    """Decode Air Handler Configuration Data (Table 154, DB ID 0x00)."""
    fan_speeds_raw = (value[0] >> 4) & 0x0F
    heat_stages_raw = (value[1] >> 4) & 0x0F
    operation_flags = value[2]
    capability_flags = value[3]
    # Table 154 encodes this 16-bit airflow value little-endian.
    max_airflow_cfm = int.from_bytes(value[6:8], "little")

    return {
        "Fan Speeds": _decode_modulating_count(fan_speeds_raw),
        "Heat Stages": _decode_modulating_count(heat_stages_raw),
        "HVAC Operation": _decode_hvac_operation(operation_flags),
        "Humidification Capable in Cool Mode": "Yes"
        if (capability_flags & 0x04)
        else "No",
        "Humidification Capable": "Yes" if (capability_flags & 0x02) else "No",
        "Dehumidification Capable": "Yes" if (capability_flags & 0x01) else "No",
        "Circulator/Blower Motor HP": _decode_fan_motor_size_hp(value[4]),
        "Circulator/Blower Motor Manufacturer": value[5],
        "Circulator/Blower Maximum Airflow": f"{max_airflow_cfm} CFM",
    }


def _decode_heat_pump_configuration_db_01(value: bytes) -> dict[str, object]:
    """Decode Heat Pump Configuration Data (Table 156, DB ID 0x01)."""
    cool_trim = int.from_bytes(value[0:1], "big", signed=True)
    heat_trim = int.from_bytes(value[1:2], "big", signed=True)
    return {
        "Cool Speed Trim Adjustment": f"{cool_trim}%",
        "Heat Speed Trim Adjustment": f"{heat_trim}%",
    }


def _decode_fan_motor_size_hp(raw_value: int) -> str:
    hp_map = {
        0: "Unavailable",
        3: "1/3 HP",
        6: "1/2 HP",
        9: "3/4 HP",
        12: "1 HP",
        24: "2 HP",
    }
    return hp_map.get(raw_value, f"Unknown encoding ({raw_value})")


def _decode_heat_pump_configuration_db_02(value: bytes) -> dict[str, object]:
    """Decode Heat Pump Configuration Data (Table 156, DB ID 0x02)."""
    # Table 155/156 encodes this 16-bit airflow value little-endian.
    max_airflow_cfm = int.from_bytes(value[2:4], "little")
    return {
        "Outdoor Motor Manufacturer": value[0],
        "Outdoor Fan Motor Size": _decode_fan_motor_size_hp(value[1]),
        "Outdoor Maximum Airflow": f"{max_airflow_cfm} CFM",
    }


def _decode_air_handler_configuration_db_01(value: bytes) -> dict[str, object]:
    """Decode Air Handler Configuration Data (Table 154, DB ID 0x01)."""
    selected_tonnage_byte = value[2]
    selected_tonnage_whole = (selected_tonnage_byte >> 4) & 0x0F
    selected_tonnage_tenths = selected_tonnage_byte & 0x0F
    selected_tonnage = selected_tonnage_whole + (selected_tonnage_tenths / 10.0)
    heat_cfm = value[3] * 10
    cool_trim = int.from_bytes(value[4:5], "big", signed=True)
    heat_trim = int.from_bytes(value[5:6], "big", signed=True)
    return {
        "Air Handler Size": f"{value[0]} kW" if value[0] != 0 else "Unavailable",
        "CFM Per Ton": value[1],
        "Selected Tonnage (manual)": f"{selected_tonnage:.1f}",
        "HEAT CFM": f"{heat_cfm} CFM",
        "Cool Speed Trim Adjustment": f"{cool_trim}%",
        "Heat Speed Trim Adjustment": f"{heat_trim}%",
    }


def _decode_furnace_configuration_db_01(value: bytes) -> dict[str, object]:
    """Decode Furnace Configuration Data (Table 153, DB ID 0x01)."""
    selected_tonnage_byte = value[1]
    selected_tonnage_whole = (selected_tonnage_byte >> 4) & 0x0F
    selected_tonnage_tenths = selected_tonnage_byte & 0x0F
    selected_tonnage = selected_tonnage_whole + (selected_tonnage_tenths / 10.0)
    heat_cfm = value[2] * 10
    cool_trim = int.from_bytes(value[3:4], "big", signed=True)
    heat_trim = int.from_bytes(value[4:5], "big", signed=True)
    return {
        "CFM Per Ton": value[0],
        "Selected Tonnage (manual)": f"{selected_tonnage:.1f}",
        "HEAT CFM": f"{heat_cfm} CFM",
        "Cool Speed Trim Adjustment": f"{cool_trim}%",
        "Heat Speed Trim Adjustment": f"{heat_trim}%",
    }


def decode_config_mdi_record(
    source_node_type: int | None, db_id: int, value: bytes
) -> tuple[dict[str, object] | None, str | None]:
    """Decode one Configuration MDI DB-ID record using source node type."""
    if source_node_type is None:
        return None, "Cannot decode configuration DB IDs without source node type context"

    if source_node_type == 5 and db_id == 0x00:
        if len(value) != 5:
            return (
                None,
                f"DB ID 0x00 length mismatch for node type {source_node_type} "
                f"({NODE_TYPE_MAP[source_node_type]}): expected 5, got {len(value)}",
            )
        return {
            "record_name": "Heat Pump Configuration Data (Table 156)",
            "node_type": source_node_type,
            "node_type_name": NODE_TYPE_MAP[source_node_type],
            "db_id": db_id,
            "raw_value": value,
            "decoded_fields": _decode_heat_pump_configuration_db_00(value),
        }, None

    if source_node_type == 2 and db_id == 0x00:
        if len(value) != 9:
            return (
                None,
                f"DB ID 0x00 length mismatch for node type {source_node_type} "
                f"({NODE_TYPE_MAP[source_node_type]}): expected 9, got {len(value)}",
            )
        return {
            "record_name": "Furnace Configuration Data (Table 153)",
            "node_type": source_node_type,
            "node_type_name": NODE_TYPE_MAP[source_node_type],
            "db_id": db_id,
            "raw_value": value,
            "decoded_fields": _decode_furnace_configuration_db_00(value),
        }, None

    if source_node_type == 3 and db_id == 0x00:
        if len(value) != 8:
            return (
                None,
                f"DB ID 0x00 length mismatch for node type {source_node_type} "
                f"({NODE_TYPE_MAP[source_node_type]}): expected 8, got {len(value)}",
            )
        return {
            "record_name": "Air Handler Configuration Data (Table 154)",
            "node_type": source_node_type,
            "node_type_name": NODE_TYPE_MAP[source_node_type],
            "db_id": db_id,
            "raw_value": value,
            "decoded_fields": _decode_air_handler_configuration_db_00(value),
        }, None

    if source_node_type == 4 and db_id == 0x00:
        if len(value) != 5:
            return (
                None,
                f"DB ID 0x00 length mismatch for node type {source_node_type} "
                f"({NODE_TYPE_MAP[source_node_type]}): expected 5, got {len(value)}",
            )
        return {
            "record_name": "Air Conditioner Configuration Data (Table 155)",
            "node_type": source_node_type,
            "node_type_name": NODE_TYPE_MAP[source_node_type],
            "db_id": db_id,
            "raw_value": value,
            "decoded_fields": _decode_air_conditioner_configuration_db_00(value),
        }, None

    if source_node_type == 5 and db_id == 0x01:
        if len(value) != 2:
            return (
                None,
                f"DB ID 0x01 length mismatch for node type {source_node_type} "
                f"({NODE_TYPE_MAP[source_node_type]}): expected 2, got {len(value)}",
            )
        return {
            "record_name": "Heat Pump Configuration Trim Data (Table 156)",
            "node_type": source_node_type,
            "node_type_name": NODE_TYPE_MAP[source_node_type],
            "db_id": db_id,
            "raw_value": value,
            "decoded_fields": _decode_heat_pump_configuration_db_01(value),
        }, None

    if source_node_type == 3 and db_id == 0x01:
        if len(value) != 6:
            return (
                None,
                f"DB ID 0x01 length mismatch for node type {source_node_type} "
                f"({NODE_TYPE_MAP[source_node_type]}): expected 6, got {len(value)}",
            )
        return {
            "record_name": "Air Handler Configuration Trim Data (Table 154)",
            "node_type": source_node_type,
            "node_type_name": NODE_TYPE_MAP[source_node_type],
            "db_id": db_id,
            "raw_value": value,
            "decoded_fields": _decode_air_handler_configuration_db_01(value),
        }, None

    if source_node_type == 2 and db_id == 0x01:
        if len(value) != 5:
            return (
                None,
                f"DB ID 0x01 length mismatch for node type {source_node_type} "
                f"({NODE_TYPE_MAP[source_node_type]}): expected 5, got {len(value)}",
            )
        return {
            "record_name": "Furnace Configuration Trim Data (Table 153)",
            "node_type": source_node_type,
            "node_type_name": NODE_TYPE_MAP[source_node_type],
            "db_id": db_id,
            "raw_value": value,
            "decoded_fields": _decode_furnace_configuration_db_01(value),
        }, None

    if source_node_type == 4 and db_id == 0x01:
        if len(value) != 1:
            return (
                None,
                f"DB ID 0x01 length mismatch for node type {source_node_type} "
                f"({NODE_TYPE_MAP[source_node_type]}): expected 1, got {len(value)}",
            )
        return {
            "record_name": "Air Conditioner Configuration Trim Data (Table 155)",
            "node_type": source_node_type,
            "node_type_name": NODE_TYPE_MAP[source_node_type],
            "db_id": db_id,
            "raw_value": value,
            "decoded_fields": {
                "Cool Speed Trim Adjustment": f"{int.from_bytes(value, 'big', signed=True)}%"
            },
        }, None

    if source_node_type == 5 and db_id == 0x02:
        if len(value) != 4:
            return (
                None,
                f"DB ID 0x02 length mismatch for node type {source_node_type} "
                f"({NODE_TYPE_MAP[source_node_type]}): expected 4, got {len(value)}",
            )
        return {
            "record_name": "Heat Pump Outdoor Motor Data (Table 156)",
            "node_type": source_node_type,
            "node_type_name": NODE_TYPE_MAP[source_node_type],
            "db_id": db_id,
            "raw_value": value,
            "decoded_fields": _decode_heat_pump_configuration_db_02(value),
        }, None

    if source_node_type == 4 and db_id == 0x02:
        if len(value) != 4:
            return (
                None,
                f"DB ID 0x02 length mismatch for node type {source_node_type} "
                f"({NODE_TYPE_MAP[source_node_type]}): expected 4, got {len(value)}",
            )
        return {
            "record_name": "Air Conditioner Outdoor Motor Data (Table 155)",
            "node_type": source_node_type,
            "node_type_name": NODE_TYPE_MAP[source_node_type],
            "db_id": db_id,
            "raw_value": value,
            "decoded_fields": _decode_heat_pump_configuration_db_02(value),
        }, None

    return (
        None,
        f"No Configuration MDI definition for node type {source_node_type} "
        f"({NODE_TYPE_MAP[source_node_type]}), DB ID 0x{db_id:02x}",
    )
