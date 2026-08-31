import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import switch
from esphome.components import uart
from esphome.const import CONF_ID

DEPENDENCIES = ["uart", "mqtt"]
AUTO_LOAD = ["switch"]

CONF_MQTT_TOPIC = "mqtt_topic"
CONF_PUBLISH_TIMEOUT_MS = "publish_timeout_ms"
CONF_MAX_FRAME_BYTES = "max_frame_bytes"
CONF_HEX_DELIMITER = "hex_delimiter"
CONF_ENABLE_RAW_MQTT_FORWARDING = "enable_raw_mqtt_forwarding"
CONF_LOCAL_NODE_TYPE = "local_node_type"
CONF_SLOT_DELAY_MS = "slot_delay_ms"
CONF_PUBLISH_STRUCTURED_EVENTS = "publish_structured_events"
CONF_AUTONET_ENABLED = "autonet_enabled"
CONF_AUTONET_SLOT_DELAY_MIN_MS = "autonet_slot_delay_min_ms"
CONF_AUTONET_SLOT_DELAY_MAX_MS = "autonet_slot_delay_max_ms"
CONF_AUTONET_KEEPALIVE_TIMEOUT_MS = "autonet_keepalive_timeout_ms"
CONF_AUTONET_DETERMINISTIC_SEED = "autonet_deterministic_seed"
CONF_LOCAL_MAC_ADDRESS = "local_mac_address"
CONF_MAC_FROM_DEVICE_IDENTITY = "mac_from_device_identity"
CONF_AUTONET_JOIN_SWITCH = "autonet_join_switch"

radish_ns = cg.esphome_ns.namespace("radish")
RadishComponent = radish_ns.class_("RadishComponent", cg.Component, uart.UARTDevice)
RadishAutoNetJoinSwitch = radish_ns.class_("RadishAutoNetJoinSwitch", switch.Switch)

CONFIG_SCHEMA = (
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(RadishComponent),
            cv.Optional(CONF_MQTT_TOPIC, default="radish/rs485/raw"): cv.string_strict,
            cv.Optional(CONF_PUBLISH_TIMEOUT_MS, default="100ms"): cv.positive_time_period_milliseconds,
            cv.Optional(CONF_MAX_FRAME_BYTES, default=256): cv.int_range(min=1, max=1024),
            cv.Optional(CONF_HEX_DELIMITER, default=" "): cv.string_strict,
            cv.Optional(CONF_ENABLE_RAW_MQTT_FORWARDING, default=True): cv.boolean,
            cv.Optional(CONF_LOCAL_NODE_TYPE, default=39): cv.int_range(min=0, max=255),
            cv.Optional(CONF_SLOT_DELAY_MS, default="250ms"): cv.positive_time_period_milliseconds,
            cv.Optional(CONF_PUBLISH_STRUCTURED_EVENTS, default=True): cv.boolean,
            cv.Optional(CONF_AUTONET_ENABLED, default=False): cv.boolean,
            cv.Optional(CONF_AUTONET_SLOT_DELAY_MIN_MS, default="100ms"): cv.positive_time_period_milliseconds,
            cv.Optional(CONF_AUTONET_SLOT_DELAY_MAX_MS, default="2500ms"): cv.positive_time_period_milliseconds,
            cv.Optional(CONF_AUTONET_KEEPALIVE_TIMEOUT_MS, default="120s"): cv.positive_time_period_milliseconds,
            cv.Optional(CONF_AUTONET_DETERMINISTIC_SEED): cv.int_range(min=0, max=0xFFFFFFFF),
            cv.Optional(CONF_LOCAL_MAC_ADDRESS): cv.string_strict,
            cv.Optional(CONF_MAC_FROM_DEVICE_IDENTITY, default=True): cv.boolean,
            cv.Optional(CONF_AUTONET_JOIN_SWITCH): switch.switch_schema(
                RadishAutoNetJoinSwitch,
                icon="mdi:lan-connect"
            ),
        }
    )
    .extend(uart.UART_DEVICE_SCHEMA)
    .extend(cv.COMPONENT_SCHEMA)
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)

    cg.add(var.set_mqtt_topic(config[CONF_MQTT_TOPIC]))
    cg.add(var.set_publish_timeout_ms(config[CONF_PUBLISH_TIMEOUT_MS].total_milliseconds))
    cg.add(var.set_max_frame_bytes(config[CONF_MAX_FRAME_BYTES]))
    cg.add(var.set_hex_delimiter(config[CONF_HEX_DELIMITER]))
    cg.add(var.set_enable_raw_mqtt_forwarding(config[CONF_ENABLE_RAW_MQTT_FORWARDING]))
    cg.add(var.set_local_node_type(config[CONF_LOCAL_NODE_TYPE]))
    cg.add(var.set_slot_delay_ms(config[CONF_SLOT_DELAY_MS].total_milliseconds))
    cg.add(var.set_publish_structured_events(config[CONF_PUBLISH_STRUCTURED_EVENTS]))
    cg.add(var.set_autonet_enabled(config[CONF_AUTONET_ENABLED]))
    cg.add(var.set_autonet_slot_delay_min_ms(config[CONF_AUTONET_SLOT_DELAY_MIN_MS].total_milliseconds))
    cg.add(var.set_autonet_slot_delay_max_ms(config[CONF_AUTONET_SLOT_DELAY_MAX_MS].total_milliseconds))
    cg.add(var.set_autonet_keepalive_timeout_ms(config[CONF_AUTONET_KEEPALIVE_TIMEOUT_MS].total_milliseconds))
    if CONF_AUTONET_DETERMINISTIC_SEED in config:
        cg.add(var.set_autonet_deterministic_seed(config[CONF_AUTONET_DETERMINISTIC_SEED]))
    if CONF_LOCAL_MAC_ADDRESS in config:
        cg.add(var.set_local_mac_address(config[CONF_LOCAL_MAC_ADDRESS]))
    cg.add(var.set_mac_from_device_identity(config[CONF_MAC_FROM_DEVICE_IDENTITY]))
    if CONF_AUTONET_JOIN_SWITCH in config:
        join_switch = cg.new_Pvariable(config[CONF_AUTONET_JOIN_SWITCH][CONF_ID])
        await switch.register_switch(join_switch, config[CONF_AUTONET_JOIN_SWITCH])
        cg.add(join_switch.set_parent(var))
        cg.add(var.set_autonet_join_switch(join_switch))
