#pragma once

#include <string>
#include <vector>

#include "ct_controller.h"
#include "esphome/components/switch/switch.h"
#include "esphome/components/uart/uart.h"
#include "esphome/core/component.h"

namespace esphome {
namespace radish {

class RadishComponent;

class RadishAutoNetJoinSwitch : public switch_::Switch {
 public:
  void set_parent(RadishComponent *parent) { this->parent_ = parent; }

 protected:
  void write_state(bool state) override;

  RadishComponent *parent_{nullptr};
};

class RadishComponent : public Component, public uart::UARTDevice {
 public:
  void setup() override;
  void loop() override;
  void dump_config() override;

  void set_mqtt_topic(const std::string &mqtt_topic) { this->mqtt_topic_ = mqtt_topic; }
  void set_publish_timeout_ms(uint32_t publish_timeout_ms) { this->publish_timeout_ms_ = publish_timeout_ms; }
  void set_max_frame_bytes(size_t max_frame_bytes) { this->max_frame_bytes_ = max_frame_bytes; }
  void set_hex_delimiter(const std::string &hex_delimiter) { this->hex_delimiter_ = hex_delimiter; }
  void set_enable_raw_mqtt_forwarding(bool enable_raw_mqtt_forwarding) {
    this->enable_raw_mqtt_forwarding_ = enable_raw_mqtt_forwarding;
    this->controller_.set_enable_raw_mqtt_forwarding(enable_raw_mqtt_forwarding);
  }
  void set_local_node_type(uint8_t local_node_type) {
    ControllerIdentity identity = this->controller_.identity();
    identity.node_type = local_node_type;
    this->controller_.set_identity(identity);
  }
  void set_local_address(uint8_t local_address) {
    ControllerIdentity identity = this->controller_.identity();
    identity.address = local_address;
    this->controller_.set_identity(identity);
  }
  void set_local_subnet(uint8_t local_subnet) {
    ControllerIdentity identity = this->controller_.identity();
    identity.subnet = local_subnet;
    this->controller_.set_identity(identity);
  }
  void set_slot_delay_ms(uint32_t slot_delay_ms) { this->controller_.set_slot_delay_ms(slot_delay_ms); }
  void set_local_mac_address(const std::string &local_mac_address) { this->local_mac_address_ = local_mac_address; }
  void set_mac_from_device_identity(bool mac_from_device_identity) {
    this->mac_from_device_identity_ = mac_from_device_identity;
  }
  void set_autonet_enabled(bool autonet_enabled) {
    this->autonet_config_.enabled = autonet_enabled;
    this->controller_.set_autonet_config(this->autonet_config_);
    if (this->autonet_join_switch_ != nullptr) {
      this->autonet_join_switch_->publish_state(autonet_enabled);
    }
  }
  void set_autonet_join_switch(switch_::Switch *autonet_join_switch) {
    this->autonet_join_switch_ = autonet_join_switch;
  }
  void set_autonet_slot_delay_min_ms(uint32_t value_ms) {
    this->autonet_config_.slot_delay_min_ms = value_ms;
    if (this->autonet_config_.slot_delay_max_ms < this->autonet_config_.slot_delay_min_ms) {
      this->autonet_config_.slot_delay_max_ms = this->autonet_config_.slot_delay_min_ms;
    }
    this->controller_.set_autonet_config(this->autonet_config_);
  }
  void set_autonet_slot_delay_max_ms(uint32_t value_ms) {
    this->autonet_config_.slot_delay_max_ms = value_ms;
    if (this->autonet_config_.slot_delay_max_ms < this->autonet_config_.slot_delay_min_ms) {
      this->autonet_config_.slot_delay_min_ms = this->autonet_config_.slot_delay_max_ms;
    }
    this->controller_.set_autonet_config(this->autonet_config_);
  }
  void set_autonet_keepalive_timeout_ms(uint32_t value_ms) {
    this->autonet_config_.keepalive_timeout_ms = value_ms;
    this->controller_.set_autonet_config(this->autonet_config_);
  }
  void set_autonet_deterministic_seed(uint32_t value) {
    this->autonet_config_.deterministic_seed = value;
    this->autonet_config_.deterministic_seed_set = true;
    this->controller_.set_autonet_config(this->autonet_config_);
  }
  void set_publish_structured_events(bool publish_structured_events) {
    this->publish_structured_events_ = publish_structured_events;
  }

 protected:
  void flush_buffer_(uint32_t now_ms);
  void send_controller_tx_(const ControllerTxAttempt &attempt);
  std::string format_hex_payload_(const std::vector<uint8_t> &data) const;
  bool publish_raw_payload_(const std::vector<uint8_t> &data) const;
  std::vector<uint8_t> parse_or_generate_local_mac_() const;
  void publish_autonet_join_switch_state_();

  std::vector<uint8_t> rx_buffer_;
  std::string mqtt_topic_{"radish/rs485/raw"};
  std::string hex_delimiter_{" "};
  uint32_t publish_timeout_ms_{100};
  uint32_t last_rx_ms_{0};
  size_t max_frame_bytes_{256};
  bool enable_raw_mqtt_forwarding_{true};
  bool publish_structured_events_{true};
  std::string local_mac_address_{};
  bool mac_from_device_identity_{true};
  switch_::Switch *autonet_join_switch_{nullptr};
  AutoNetConfig autonet_config_{};
  CtController controller_{};
};

}  // namespace radish
}  // namespace esphome
