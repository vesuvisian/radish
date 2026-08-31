#include "radish.h"

#include <array>
#include <cctype>
#include <cstdlib>
#include <cstdio>
#include <inttypes.h>

#include "esphome/components/mqtt/mqtt_client.h"
#include "esphome/core/hal.h"
#include "esphome/core/log.h"
#ifdef USE_ESP32
#include "esp_mac.h"
#include "esp_system.h"
#endif

namespace esphome {
namespace radish {

static const char *const TAG = "radish.component";

void RadishAutoNetJoinSwitch::write_state(bool state) {
  if (this->parent_ != nullptr) {
    this->parent_->set_autonet_enabled(state);
    return;
  }
  this->publish_state(state);
}

void RadishComponent::setup() {
  this->controller_.setup();
  this->rx_buffer_.reserve(this->max_frame_bytes_);
  ControllerIdentity identity = this->controller_.identity();
  identity.mac_address = this->parse_or_generate_local_mac_();
  if (identity.session_id == std::vector<uint8_t>{0, 0, 0, 0, 0, 0, 0, 1}) {
#ifdef USE_ESP32
    const uint32_t random_value = esp_random();
#else
    const uint32_t random_value = millis();
#endif
    identity.session_id = {0x00, 0x00, 0x09, static_cast<uint8_t>((random_value >> 24) & 0xFF),
                           static_cast<uint8_t>((random_value >> 16) & 0xFF), static_cast<uint8_t>((random_value >> 8) & 0xFF),
                           static_cast<uint8_t>(random_value & 0xFF), 0x01};
  }
  this->controller_.set_identity(identity);
  this->controller_.set_autonet_config(this->autonet_config_);
  this->publish_autonet_join_switch_state_();
}

void RadishComponent::loop() {
  const uint32_t now = millis();
  bool read_any = false;

  while (this->available() > 0) {
    uint8_t byte;
    if (!this->read_byte(&byte)) {
      break;
    }

    read_any = true;
    this->rx_buffer_.push_back(byte);

    if (this->rx_buffer_.size() >= this->max_frame_bytes_) {
      this->flush_buffer_(now);
      break;
    }
  }

  if (read_any) {
    this->last_rx_ms_ = now;
  }

  if (!this->rx_buffer_.empty() && ((now - this->last_rx_ms_) >= this->publish_timeout_ms_)) {
    this->flush_buffer_(now);
  }

  ControllerStepResult tick_result = this->controller_.tick(now);
  for (const ControllerTxAttempt &attempt : tick_result.tx_attempts) {
    this->send_controller_tx_(attempt);
  }
}

void RadishComponent::dump_config() {
  ESP_LOGCONFIG(TAG, "Radish Component:");
  ESP_LOGCONFIG(TAG, "  MQTT topic: %s", this->mqtt_topic_.c_str());
  ESP_LOGCONFIG(TAG, "  Publish timeout: %" PRIu32 " ms", this->publish_timeout_ms_);
  ESP_LOGCONFIG(TAG, "  Max frame bytes: %u", static_cast<unsigned>(this->max_frame_bytes_));
  ESP_LOGCONFIG(TAG, "  Hex delimiter: '%s'", this->hex_delimiter_.c_str());
  const ControllerIdentity &identity = this->controller_.identity();
  ESP_LOGCONFIG(TAG, "  Local address: 0x%02X", identity.address);
  ESP_LOGCONFIG(TAG, "  Local subnet: 0x%02X", identity.subnet);
  ESP_LOGCONFIG(TAG, "  Local node type: 0x%02X", identity.node_type);
  ESP_LOGCONFIG(TAG, "  AutoNet join enabled: %s", this->autonet_config_.enabled ? "yes" : "no");
  ESP_LOGCONFIG(TAG, "  Publish structured events: %s", this->publish_structured_events_ ? "yes" : "no");
}

void RadishComponent::flush_buffer_(uint32_t now_ms) {
  if (this->rx_buffer_.empty()) {
    return;
  }

  ControllerStepResult result = this->controller_.on_raw_chunk(this->rx_buffer_, now_ms);
  if (result.should_publish_raw) {
    this->publish_raw_payload_(this->rx_buffer_);
  }
  for (const ControllerTxAttempt &attempt : result.tx_attempts) {
    this->send_controller_tx_(attempt);
  }
  this->rx_buffer_.clear();
}

void RadishComponent::send_controller_tx_(const ControllerTxAttempt &attempt) {
  if (attempt.bytes.empty()) {
    return;
  }
  this->write_array(attempt.bytes);
  this->flush();
  if (this->enable_raw_mqtt_forwarding_) {
    this->publish_raw_payload_(attempt.bytes);
  }
}

bool RadishComponent::publish_raw_payload_(const std::vector<uint8_t> &data) const {
  auto *mqtt_client = mqtt::global_mqtt_client;
  if (mqtt_client == nullptr || !mqtt_client->is_connected()) {
    ESP_LOGW(TAG, "MQTT unavailable, dropping %u buffered byte(s)", static_cast<unsigned>(data.size()));
    return false;
  }
  const std::string payload = this->format_hex_payload_(data);
  const bool ok = mqtt_client->publish(this->mqtt_topic_, payload);
  if (!ok) {
    ESP_LOGW(TAG, "Failed to publish %u byte(s) to MQTT", static_cast<unsigned>(data.size()));
  }
  return ok;
}

std::vector<uint8_t> RadishComponent::parse_or_generate_local_mac_() const {
  auto build_from_seed = [](uint64_t seed) -> std::vector<uint8_t> {
    return {
        0x00,
        0x00,
        0x09,
        static_cast<uint8_t>((seed >> 32) & 0xFF),
        static_cast<uint8_t>((seed >> 24) & 0xFF),
        static_cast<uint8_t>((seed >> 16) & 0xFF),
        static_cast<uint8_t>((seed >> 8) & 0xFF),
        static_cast<uint8_t>(seed & 0xFF),
    };
  };

  if (!this->local_mac_address_.empty()) {
    std::vector<uint8_t> parsed;
    std::string token;
    token.reserve(2);
    for (char ch : this->local_mac_address_) {
      if (ch == ':' || ch == '-') {
        if (!token.empty()) {
          parsed.push_back(static_cast<uint8_t>(std::strtoul(token.c_str(), nullptr, 16)));
          token.clear();
        }
        continue;
      }
      if (std::isxdigit(static_cast<unsigned char>(ch))) {
        token.push_back(ch);
      }
      if (token.size() == 2) {
        parsed.push_back(static_cast<uint8_t>(std::strtoul(token.c_str(), nullptr, 16)));
        token.clear();
      }
    }
    if (!token.empty()) {
      parsed.push_back(static_cast<uint8_t>(std::strtoul(token.c_str(), nullptr, 16)));
    }
    if (parsed.size() == 8 && parsed[0] == 0x00 && parsed[1] == 0x00 && parsed[2] == 0x09) {
      return parsed;
    }
    ESP_LOGW(TAG, "Invalid local_mac_address. Must be 8 bytes starting with 00:00:09. Falling back to generated MAC.");
  }

  if (!this->mac_from_device_identity_) {
    return build_from_seed(0x0000090000000001ULL);
  }

#ifdef USE_ESP32
  std::array<uint8_t, 6> sta_mac{};
  if (esp_read_mac(sta_mac.data(), ESP_MAC_WIFI_STA) == ESP_OK) {
    const uint64_t seed = (static_cast<uint64_t>(sta_mac[0]) << 40) | (static_cast<uint64_t>(sta_mac[1]) << 32) |
                          (static_cast<uint64_t>(sta_mac[2]) << 24) | (static_cast<uint64_t>(sta_mac[3]) << 16) |
                          (static_cast<uint64_t>(sta_mac[4]) << 8) | static_cast<uint64_t>(sta_mac[5]);
    return build_from_seed(seed);
  }
  ESP_LOGW(TAG, "Failed to read WiFi STA MAC. Falling back to deterministic MAC.");
#endif
  return build_from_seed(0x0000090000000001ULL);
}

std::string RadishComponent::format_hex_payload_(const std::vector<uint8_t> &data) const {
  if (data.empty()) {
    return "";
  }

  std::string payload;
  payload.reserve(data.size() * 3);

  char buf[3];
  for (size_t i = 0; i < data.size(); ++i) {
    std::snprintf(buf, sizeof(buf), "%02X", data[i]);
    payload += buf;
    if (i + 1 < data.size()) {
      payload += this->hex_delimiter_;
    }
  }

  if (this->hex_delimiter_ == " ") {
    payload += " ";
  }

  return payload;
}

void RadishComponent::publish_autonet_join_switch_state_() {
  if (this->autonet_join_switch_ == nullptr) {
    return;
  }
  this->autonet_join_switch_->publish_state(this->autonet_config_.enabled);
}

}  // namespace radish
}  // namespace esphome
