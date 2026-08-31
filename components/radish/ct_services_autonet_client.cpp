#include "ct_services_autonet_client.h"

#include <algorithm>

#include "esphome/core/log.h"

namespace esphome {
namespace radish {

static const char *const TAG = "radish.autonet";

static const char *autonet_state_to_string(AutoNetClientState state) {
  switch (state) {
    case AutoNetClientState::UNADDRESSED:
      return "UNADDRESSED";
    case AutoNetClientState::AWAITING_SLOT_DELAY_FOR_DISCOVERY_RESPONSE:
      return "AWAITING_SLOT_DELAY_FOR_DISCOVERY_RESPONSE";
    case AutoNetClientState::AWAITING_SET_ADDRESS:
      return "AWAITING_SET_ADDRESS";
    case AutoNetClientState::ADDRESSED_ACTIVE:
      return "ADDRESSED_ACTIVE";
    case AutoNetClientState::RELINQUISH_PENDING:
      return "RELINQUISH_PENDING";
    default:
      return "UNKNOWN";
  }
}

ServiceOutput AutoNetClient::force_unaddressed() {
  ServiceOutput output;
  output.autonet_state = this->state_;
  ESP_LOGI(TAG, "Force unaddress requested (join disabled). Current state=%s",
           autonet_state_to_string(this->state_));
  enter_unaddressed_(&output);
  return output;
}

std::vector<uint8_t> AutoNetClient::generate_session_id_(const ControllerIdentity &identity, uint32_t now_ms) {
  uint64_t seed = static_cast<uint64_t>(now_ms) << 32;
  seed ^= static_cast<uint64_t>(this->sequence_counter_++) << 8;
  for (uint8_t b : identity.mac_address) {
    seed = (seed * 1099511628211ULL) ^ static_cast<uint64_t>(b);
  }
  std::vector<uint8_t> session(8, 0);
  for (size_t i = 0; i < session.size(); ++i) {
    session[i] = static_cast<uint8_t>((seed >> ((7U - static_cast<uint32_t>(i)) * 8U)) & 0xFFU);
  }
  bool all_zero = true;
  for (uint8_t b : session) {
    if (b != 0) {
      all_zero = false;
      break;
    }
  }
  if (all_zero) {
    session.back() = 0x01;
  }
  return session;
}

uint32_t AutoNetClient::compute_slot_delay_ms_(const CtFrame &frame, const ControllerIdentity &identity) {
  const uint32_t min_delay = this->config_.slot_delay_min_ms;
  const uint32_t max_delay = this->config_.slot_delay_max_ms;
  const uint32_t range = (max_delay > min_delay) ? (max_delay - min_delay + 1U) : 1U;
  uint32_t hash = this->config_.deterministic_seed_set ? this->config_.deterministic_seed : 0xA55A5AA5U;
  hash ^= static_cast<uint32_t>(identity.node_type) << 24;
  hash ^= static_cast<uint32_t>(identity.address) << 16;
  hash ^= static_cast<uint32_t>(frame.source_address) << 8;
  hash ^= static_cast<uint32_t>(frame.packet_number);
  hash ^= this->sequence_counter_++;
  for (uint8_t b : identity.mac_address) {
    hash = (hash * 33U) ^ b;
  }
  return min_delay + (hash % range);
}

bool AutoNetClient::is_node_discovery_for_this_type_(const CtFrame &frame, uint8_t local_node_type) {
  if (frame.message_type != CT_MSG_TYPE_NODE_DISCOVERY_REQUEST) {
    return false;
  }
  if (frame.payload.empty()) {
    return true;
  }
  const uint8_t filter = frame.payload[0];
  return filter == 0x00 || filter == local_node_type;
}

bool AutoNetClient::is_set_address_for_this_identity_(const CtFrame &frame, const ControllerIdentity &identity) {
  if (frame.message_type != CT_MSG_TYPE_SET_ADDRESS_REQUEST) {
    return false;
  }
  if (frame.destination_address != CT_ADDRESS_BROADCAST || frame.subnet != CT_SUBNET_BROADCAST) {
    return false;
  }
  if (frame.payload.size() < 19) {
    return false;
  }
  const bool write_enabled = frame.payload[18] == 0x01;
  if (!write_enabled) {
    return false;
  }
  const bool mac_match =
      std::equal(identity.mac_address.begin(), identity.mac_address.end(), frame.payload.begin() + 2);
  const bool session_match =
      std::equal(identity.session_id.begin(), identity.session_id.end(), frame.payload.begin() + 10);
  return mac_match && session_match;
}

bool AutoNetClient::is_get_node_id_for_this_identity_(const CtFrame &frame, const ControllerIdentity &identity) {
  if (frame.message_type != CT_MSG_TYPE_GET_NODE_ID_REQUEST) {
    return false;
  }
  return frame.destination_address == identity.address && frame.subnet == identity.subnet;
}

QueuedTx AutoNetClient::build_node_discovery_response_(const CtFrame &frame, const ControllerIdentity &identity) {
  CtFrame response;
  response.destination_address = frame.source_address;
  response.source_address = identity.address;
  response.subnet = identity.subnet;
  response.send_method = frame.send_method;
  response.send_parameters = frame.send_parameters;
  response.source_node_type = identity.node_type;
  response.message_type = CT_MSG_TYPE_NODE_DISCOVERY_RESPONSE;
  response.packet_number = static_cast<uint8_t>(frame.packet_number & ~CT_PACKET_FLAG_VERSION);
  response.payload.push_back(identity.node_type);
  response.payload.push_back(0x00);  // Reserved
  response.payload.insert(response.payload.end(), identity.mac_address.begin(), identity.mac_address.end());
  response.payload.insert(response.payload.end(), identity.session_id.begin(), identity.session_id.end());
  return QueuedTx{TxSource::AUTONET_CLIENT, response};
}

QueuedTx AutoNetClient::build_address_confirmation_response_(const CtFrame &frame, const ControllerIdentity &identity) {
  CtFrame response = frame;
  response.destination_address = frame.source_address;
  response.source_address = identity.address;
  response.subnet = identity.subnet;
  response.source_node_type = identity.node_type;
  response.message_type = CT_MSG_TYPE_ADDRESS_CONFIRMATION_RESPONSE;
  return QueuedTx{TxSource::AUTONET_CLIENT, response};
}

QueuedTx AutoNetClient::build_set_address_response_(const CtFrame &frame, const ControllerIdentity &identity,
                                                    uint8_t assigned_address, uint8_t assigned_subnet) {
  CtFrame ack = frame;
  ack.destination_address = frame.source_address;
  ack.source_address = assigned_address;
  ack.subnet = assigned_subnet;
  ack.source_node_type = identity.node_type;
  ack.message_type = CT_MSG_TYPE_SET_ADDRESS_RESPONSE;
  return QueuedTx{TxSource::AUTONET_CLIENT, ack};
}

QueuedTx AutoNetClient::build_get_node_id_response_(const CtFrame &frame, const ControllerIdentity &identity) {
  CtFrame response;
  response.destination_address = frame.source_address;
  response.source_address = identity.address;
  response.subnet = identity.subnet;
  response.send_method = frame.send_method;
  response.send_parameters = frame.send_parameters;
  response.source_node_type = identity.node_type;
  response.message_type = CT_MSG_TYPE_GET_NODE_ID_RESPONSE;
  response.packet_number = frame.packet_number;
  response.payload.reserve(17);
  response.payload.push_back(identity.node_type);
  response.payload.insert(response.payload.end(), identity.mac_address.begin(), identity.mac_address.end());
  response.payload.insert(response.payload.end(), identity.session_id.begin(), identity.session_id.end());
  return QueuedTx{TxSource::AUTONET_CLIENT, response};
}

bool AutoNetClient::is_address_confirmation_valid_(const CtFrame &frame, const ControllerIdentity &identity) const {
  if (identity.address == 0 || identity.subnet != CT_SUBNET_V2 || frame.payload.empty()) {
    return true;
  }
  const size_t index = static_cast<size_t>(identity.address);
  if (index >= frame.payload.size()) {
    return false;
  }
  return frame.payload[index] == identity.node_type;
}

void AutoNetClient::enter_unaddressed_(ServiceOutput *output) {
  const AutoNetClientState prior_state = this->state_;
  this->state_ = AutoNetClientState::UNADDRESSED;
  this->slot_delay_due_ms_ = 0;
  this->pending_discovery_request_ = CtFrame{};
  this->pending_address_confirmation_response_ = false;
  this->pending_address_confirmation_due_ms_ = 0;
  this->pending_address_confirmation_frame_ = CtFrame{};
  this->expected_r2r_coordinator_mac_.clear();
  this->expected_r2r_coordinator_session_.clear();
  output->clear_assignment = true;
  output->autonet_state = this->state_;
  ESP_LOGI(TAG, "State -> %s (from %s); clearing address/subnet assignment",
           autonet_state_to_string(this->state_), autonet_state_to_string(prior_state));
}

bool AutoNetClient::validate_or_capture_r2r_coordinator_(const CtFrame &frame, const ControllerIdentity &identity,
                                                          ServiceOutput *output) {
  if (frame.message_type != CT_MSG_TYPE_R2R) {
    return true;
  }
  if (frame.destination_address != identity.address || frame.subnet != identity.subnet || identity.address == 0) {
    return true;
  }
  if (frame.payload.size() < 17 || frame.payload[0] != CT_R2R_CODE_REQUEST) {
    ESP_LOGW(TAG, "Invalid coordinator R2R while addressed; relinquishing");
    enter_unaddressed_(output);
    return false;
  }
  const std::vector<uint8_t> coordinator_mac(frame.payload.begin() + 1, frame.payload.begin() + 9);
  const std::vector<uint8_t> coordinator_session(frame.payload.begin() + 9, frame.payload.begin() + 17);
  if (this->expected_r2r_coordinator_mac_.empty() || this->expected_r2r_coordinator_session_.empty()) {
    this->expected_r2r_coordinator_mac_ = coordinator_mac;
    this->expected_r2r_coordinator_session_ = coordinator_session;
    return true;
  }
  if (this->expected_r2r_coordinator_mac_ != coordinator_mac ||
      this->expected_r2r_coordinator_session_ != coordinator_session) {
    ESP_LOGW(TAG, "Coordinator identity changed (MAC/session mismatch); relinquishing");
    enter_unaddressed_(output);
    return false;
  }
  return true;
}

ServiceOutput AutoNetClient::on_frame(const CtFrame &frame, const ControllerIdentity &identity, uint32_t now_ms) {
  ServiceOutput output;
  output.autonet_state = this->state_;

  if (!this->config_.enabled) {
    return output;
  }

  if (!validate_or_capture_r2r_coordinator_(frame, identity, &output)) {
    return output;
  }

  if (this->pending_address_confirmation_response_) {
    this->pending_address_confirmation_response_ = false;
    this->pending_address_confirmation_due_ms_ = 0;
    this->pending_address_confirmation_frame_ = CtFrame{};
  }

  if (frame.message_type == CT_MSG_TYPE_ADDRESS_CONFIRMATION_PUSH &&
      (frame.subnet == CT_SUBNET_V2 || frame.subnet == CT_SUBNET_BROADCAST)) {
    output.saw_address_confirmation = true;
    this->last_address_confirmation_ms_ = now_ms;

    const bool is_broadcast = (frame.destination_address == CT_ADDRESS_BROADCAST);
    if (is_broadcast) {
      if (identity.address != 0) {
        this->pending_address_confirmation_response_ = true;
        this->pending_address_confirmation_due_ms_ = now_ms + compute_slot_delay_ms_(frame, identity);
        this->pending_address_confirmation_frame_ = frame;
        ESP_LOGD(TAG, "Keep-alive broadcast seen; scheduling response in %u ms",
                 static_cast<unsigned>(this->pending_address_confirmation_due_ms_ - now_ms));
      }
    } else if (frame.destination_address == identity.address && frame.subnet == identity.subnet) {
      ESP_LOGD(TAG, "Keep-alive addressed to local node; responding immediately");
      output.queued.push_back(build_address_confirmation_response_(frame, identity));
    }

    if (!is_address_confirmation_valid_(frame, identity)) {
      ESP_LOGW(TAG, "Address confirmation validation failed (node list mismatch); relinquishing");
      enter_unaddressed_(&output);
    }
    return output;
  }

  if (this->state_ == AutoNetClientState::AWAITING_SLOT_DELAY_FOR_DISCOVERY_RESPONSE) {
    ESP_LOGD(TAG, "Discovery slot-delay canceled by bus activity; state -> UNADDRESSED");
    this->state_ = AutoNetClientState::UNADDRESSED;
    output.autonet_state = this->state_;
  }

  if (this->state_ == AutoNetClientState::UNADDRESSED &&
      is_node_discovery_for_this_type_(frame, identity.node_type)) {
    output.updated_session_id = generate_session_id_(identity, now_ms);
    this->pending_discovery_request_ = frame;
    this->slot_delay_due_ms_ = now_ms + compute_slot_delay_ms_(frame, identity);
    this->state_ = AutoNetClientState::AWAITING_SLOT_DELAY_FOR_DISCOVERY_RESPONSE;
    output.autonet_state = this->state_;
    ESP_LOGI(TAG, "Node discovery matched (node_type=%u); slot-delay=%u ms; state -> %s",
             static_cast<unsigned>(identity.node_type),
             static_cast<unsigned>(this->slot_delay_due_ms_ - now_ms),
             autonet_state_to_string(this->state_));
    return output;
  }

  if (is_set_address_for_this_identity_(frame, identity)) {
    const uint8_t assigned_address = frame.payload[0];
    const uint8_t assigned_subnet = frame.payload[1];
    output.queued.push_back(build_set_address_response_(frame, identity, assigned_address, assigned_subnet));
    if (frame.payload[0] == 0 && frame.payload[1] == 0) {
      this->state_ = AutoNetClientState::RELINQUISH_PENDING;
      output.autonet_state = this->state_;
      ESP_LOGI(TAG, "Received SetAddress 0/0 relinquish request; state -> %s",
               autonet_state_to_string(this->state_));
      enter_unaddressed_(&output);
      return output;
    }
    output.assigned_address = assigned_address;
    output.assigned_subnet = assigned_subnet;
    this->last_address_confirmation_ms_ = now_ms;
    this->state_ = AutoNetClientState::ADDRESSED_ACTIVE;
    output.autonet_state = this->state_;
    ESP_LOGI(TAG, "Accepted address assignment addr=0x%02X subnet=0x%02X; state -> %s",
             frame.payload[0], frame.payload[1], autonet_state_to_string(this->state_));
    return output;
  }

  if (is_get_node_id_for_this_identity_(frame, identity)) {
    output.queued.push_back(build_get_node_id_response_(frame, identity));
    return output;
  }
  return output;
}

ServiceOutput AutoNetClient::on_tick(const ControllerIdentity &identity, uint32_t now_ms) {
  ServiceOutput output;
  output.autonet_state = this->state_;
  if (!this->config_.enabled) {
    return output;
  }

  if (this->state_ == AutoNetClientState::AWAITING_SLOT_DELAY_FOR_DISCOVERY_RESPONSE &&
      now_ms >= this->slot_delay_due_ms_) {
    output.queued.push_back(build_node_discovery_response_(this->pending_discovery_request_, identity));
    this->state_ = AutoNetClientState::AWAITING_SET_ADDRESS;
    output.autonet_state = this->state_;
    ESP_LOGI(TAG, "Discovery response slot elapsed; enqueued NodeDiscoveryResponse; state -> %s",
             autonet_state_to_string(this->state_));
    return output;
  }

  if (this->pending_address_confirmation_response_ && now_ms >= this->pending_address_confirmation_due_ms_) {
    output.queued.push_back(build_address_confirmation_response_(this->pending_address_confirmation_frame_, identity));
    this->pending_address_confirmation_response_ = false;
    this->pending_address_confirmation_due_ms_ = 0;
    this->pending_address_confirmation_frame_ = CtFrame{};
    ESP_LOGD(TAG, "Keep-alive broadcast slot elapsed; enqueued AddressConfirmation response");
    return output;
  }

  if (this->state_ == AutoNetClientState::ADDRESSED_ACTIVE && identity.subnet == CT_SUBNET_V2 &&
      this->last_address_confirmation_ms_ > 0 &&
      (now_ms - this->last_address_confirmation_ms_) >= this->config_.keepalive_timeout_ms) {
    ESP_LOGW(TAG, "Keep-alive timeout (%u ms) exceeded; relinquishing",
             static_cast<unsigned>(this->config_.keepalive_timeout_ms));
    enter_unaddressed_(&output);
    return output;
  }
  return output;
}

}  // namespace radish
}  // namespace esphome
