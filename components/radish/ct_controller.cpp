#include "ct_controller.h"

#include <algorithm>

#include "ct_frame_codec.h"
#include "esphome/core/log.h"

namespace esphome {
namespace radish {

static const char *const TAG = "radish.controller";

static bool is_response_message_type(uint8_t message_type) { return (message_type & 0x80U) != 0; }

void CtController::set_autonet_config(const AutoNetConfig &config) {
  const bool was_enabled = this->autonet_config_.enabled;
  this->autonet_config_ = config;
  this->autonet_client_.set_config(config);
  if (was_enabled != config.enabled) {
    ESP_LOGI(TAG, "AutoNet join %s", config.enabled ? "ENABLED" : "DISABLED");
  }
  if (was_enabled && !config.enabled) {
    ServiceOutput relinquish = this->autonet_client_.force_unaddressed();
    if (relinquish.clear_assignment) {
      this->clear_pending_tx_state_();
      this->identity_.address = 0;
      this->identity_.subnet = CT_SUBNET_V2;
      ESP_LOGI(TAG, "Local identity assignment cleared (addr=0x00 subnet=0x%02X)", CT_SUBNET_V2);
    }
  }
}

ControllerStepResult CtController::on_raw_chunk(const std::vector<uint8_t> &raw_bytes, uint32_t now_ms) {
  ControllerStepResult out;
  this->counters_.raw_chunks_seen++;
  this->counters_.raw_bytes_seen += static_cast<uint32_t>(raw_bytes.size());
  this->last_rx_ms_ = now_ms;
  this->bus_epoch_++;
  out.should_publish_raw = this->enable_raw_mqtt_forwarding_;

  const CtParseResult parse = CtFrameCodec::parse_frames(raw_bytes);
  this->counters_.frames_checksum_failed += parse.checksum_failures;
  this->counters_.frames_truncated += parse.truncated_frames;

  for (const CtFrame &frame : parse.frames) {
    this->counters_.frames_valid++;
    this->maybe_reset_dataflow_cycle_(frame, now_ms);
    ControllerStepResult per_frame = this->handle_frame_(frame, now_ms);
    out.tx_attempts.insert(out.tx_attempts.end(), per_frame.tx_attempts.begin(), per_frame.tx_attempts.end());
  }
  return out;
}

ControllerStepResult CtController::tick(uint32_t now_ms) {
  ControllerStepResult out;
  ServiceOutput autonet_tick = this->autonet_client_.on_tick(this->identity_, now_ms);
  if (autonet_tick.clear_assignment || autonet_tick.assigned_address.has_value() || autonet_tick.assigned_subnet.has_value()) {
    this->clear_pending_tx_state_();
  }
  this->append_service_outputs_(autonet_tick, &out);
  if (autonet_tick.updated_session_id.has_value()) {
    this->identity_.session_id = autonet_tick.updated_session_id.value();
  }
  if (autonet_tick.clear_assignment) {
    this->identity_.address = 0;
    this->identity_.subnet = CT_SUBNET_V2;
  }
  if (autonet_tick.assigned_address.has_value()) {
    this->identity_.address = autonet_tick.assigned_address.value();
  }
  if (autonet_tick.assigned_subnet.has_value()) {
    this->identity_.subnet = autonet_tick.assigned_subnet.value();
  }

  if (this->pending_token_offer_) {
    if (this->bus_epoch_ != this->pending_token_epoch_) {
      this->pending_token_offer_ = false;
    } else if (now_ms >= this->pending_token_due_ms_) {
      this->pending_token_offer_ = false;
      if (!this->token_offer_sent_this_cycle_ && !this->tx_queue_.empty()) {
        this->token_offer_sent_this_cycle_ = true;
        ControllerStepResult send = this->try_send_now_(make_token_offer_response_(this->pending_token_offer_frame_));
        out.tx_attempts.insert(out.tx_attempts.end(), send.tx_attempts.begin(), send.tx_attempts.end());
      }
    }
  }
  return out;
}

bool CtController::enqueue_outbound(const QueuedTx &queued_tx) {
  if (this->tx_queue_.size() >= this->max_tx_queue_depth_) {
    this->counters_.queue_dropped++;
    return false;
  }
  this->tx_queue_.push_back(queued_tx);
  return true;
}

ControllerStepResult CtController::handle_frame_(const CtFrame &frame, uint32_t now_ms) {
  ControllerStepResult out;
  const bool is_local_non_dataflow_non_r2r =
      this->is_for_local_node_(frame) && !is_dataflow_packet(frame.packet_number) &&
      frame.message_type != CT_MSG_TYPE_R2R && frame.message_type != CT_MSG_TYPE_ADDRESS_CONFIRMATION_PUSH &&
      frame.message_type != CT_MSG_TYPE_GET_NODE_ID_REQUEST;
  const bool is_local_non_dataflow_get_node_id_request =
      this->is_for_local_node_(frame) && !is_dataflow_packet(frame.packet_number) &&
      frame.message_type == CT_MSG_TYPE_GET_NODE_ID_REQUEST;

  if (is_local_non_dataflow_get_node_id_request) {
    ControllerStepResult ack_result = this->try_send_now_(this->make_non_dataflow_ack_(frame));
    out.tx_attempts.insert(out.tx_attempts.end(), ack_result.tx_attempts.begin(), ack_result.tx_attempts.end());
  }

  ServiceOutput autonet_output = this->autonet_client_.on_frame(frame, this->identity_, now_ms);
  if (autonet_output.clear_assignment || autonet_output.assigned_address.has_value() ||
      autonet_output.assigned_subnet.has_value()) {
    this->clear_pending_tx_state_();
  }
  this->append_service_outputs_(autonet_output, &out);
  if (autonet_output.updated_session_id.has_value()) {
    this->identity_.session_id = autonet_output.updated_session_id.value();
  }
  if (autonet_output.clear_assignment) {
    this->identity_.address = 0;
    this->identity_.subnet = CT_SUBNET_V2;
  }
  if (autonet_output.assigned_address.has_value()) {
    this->identity_.address = autonet_output.assigned_address.value();
  }
  if (autonet_output.assigned_subnet.has_value()) {
    this->identity_.subnet = autonet_output.assigned_subnet.value();
  }

  ServiceOutput subordinate_output = this->subordinate_service_.on_frame(frame, this->identity_);
  this->append_service_outputs_(subordinate_output, &out);

  if (is_local_non_dataflow_non_r2r) {
    ControllerStepResult ack_result = this->try_send_now_(this->make_non_dataflow_ack_(frame));
    out.tx_attempts.insert(out.tx_attempts.end(), ack_result.tx_attempts.begin(), ack_result.tx_attempts.end());
  }

  if (this->is_subnet3_token_offer_(frame)) {
    if (!this->tx_queue_.empty() && !this->token_offer_sent_this_cycle_) {
      this->pending_token_offer_ = true;
      this->pending_token_offer_frame_ = frame;
      this->pending_token_due_ms_ = now_ms + this->slot_delay_ms_;
      this->pending_token_epoch_ = this->bus_epoch_;
    }
    return out;
  }

  if (frame.message_type == CT_MSG_TYPE_R2R && this->is_for_local_node_(frame)) {
    ControllerStepResult send_result;
    if (this->tx_queue_.empty()) {
      send_result = this->try_send_now_(this->make_r2r_ack_(frame));
    } else {
      send_result = this->send_next_queued_(TxSource::CONTROLLER);
    }
    out.tx_attempts.insert(out.tx_attempts.end(), send_result.tx_attempts.begin(), send_result.tx_attempts.end());
    return out;
  }

  if (!this->is_for_local_node_(frame)) {
    this->counters_.frames_filtered++;
  }
  return out;
}

void CtController::append_service_outputs_(const ServiceOutput &service_output, ControllerStepResult *out) {
  for (const QueuedTx &queued : service_output.queued) {
    // Keep-alive and discovery responses should be emitted promptly once slot-delay
    // gating has been satisfied by the service state machines.
    if (queued.frame.message_type == CT_MSG_TYPE_ADDRESS_CONFIRMATION_RESPONSE ||
        queued.frame.message_type == CT_MSG_TYPE_SET_ADDRESS_RESPONSE ||
        queued.frame.message_type == CT_MSG_TYPE_NODE_DISCOVERY_RESPONSE) {
      ControllerStepResult send = this->try_send_now_(queued);
      if (!send.tx_attempts.empty()) {
        out->tx_attempts.insert(out->tx_attempts.end(), send.tx_attempts.begin(), send.tx_attempts.end());
        continue;
      }
    }
    this->enqueue_outbound(queued);
  }
}

void CtController::clear_pending_tx_state_() {
  this->tx_queue_.clear();
  this->pending_token_offer_ = false;
  this->token_offer_sent_this_cycle_ = false;
}

void CtController::maybe_reset_dataflow_cycle_(const CtFrame &frame, uint32_t now_ms) {
  if (frame.message_type == CT_MSG_TYPE_ADDRESS_CONFIRMATION_PUSH && frame.subnet == CT_SUBNET_V2) {
    this->token_offer_sent_this_cycle_ = false;
    this->pending_token_offer_ = false;
    this->last_cycle_reset_ms_ = now_ms;
    return;
  }
  if ((now_ms - this->last_cycle_reset_ms_) > 120000U) {
    this->token_offer_sent_this_cycle_ = false;
    this->pending_token_offer_ = false;
    this->last_cycle_reset_ms_ = now_ms;
  }
}

bool CtController::is_for_local_node_(const CtFrame &frame) const {
  if (this->identity_.address == CT_ADDRESS_BROADCAST || frame.destination_address == CT_ADDRESS_BROADCAST) {
    return false;
  }
  const bool address_match = frame.destination_address == this->identity_.address;
  const bool subnet_match = frame.subnet == this->identity_.subnet;
  return address_match && subnet_match;
}

bool CtController::is_subnet3_token_offer_(const CtFrame &frame) const {
  if (frame.message_type != CT_MSG_TYPE_TOKEN_OFFER) {
    return false;
  }
  const bool subnet_match = frame.subnet == CT_SUBNET_V2 || frame.subnet == CT_SUBNET_BROADCAST;
  return subnet_match;
}

QueuedTx CtController::make_r2r_ack_(const CtFrame &r2r) const {
  CtFrame ack;
  ack.destination_address = r2r.source_address;
  ack.source_address = this->identity_.address;
  ack.subnet = this->identity_.subnet;
  ack.send_method = r2r.send_method;
  ack.send_parameters = r2r.send_parameters;
  ack.source_node_type = this->identity_.node_type;
  ack.message_type = CT_MSG_TYPE_R2R;
  ack.packet_number = static_cast<uint8_t>(r2r.packet_number | CT_PACKET_FLAG_DATAFLOW);
  ack.payload.reserve(17);
  ack.payload.push_back(CT_R2R_CODE_ACK);
  ack.payload.insert(ack.payload.end(), this->identity_.mac_address.begin(), this->identity_.mac_address.end());
  ack.payload.insert(ack.payload.end(), this->identity_.session_id.begin(), this->identity_.session_id.end());
  return QueuedTx{TxSource::CONTROLLER, ack};
}

QueuedTx CtController::make_non_dataflow_ack_(const CtFrame &frame) const {
  CtFrame ack;
  ack.destination_address = frame.source_address;
  ack.source_address = this->identity_.address;
  ack.subnet = this->identity_.subnet;
  ack.send_method = frame.send_method;
  ack.send_parameters = frame.send_parameters;
  ack.source_node_type = this->identity_.node_type;
  ack.message_type = frame.message_type;
  ack.packet_number = static_cast<uint8_t>(frame.packet_number | CT_PACKET_FLAG_DATAFLOW);
  ack.payload.reserve(17);
  ack.payload.push_back(CT_R2R_CODE_ACK);
  ack.payload.insert(ack.payload.end(), this->identity_.mac_address.begin(), this->identity_.mac_address.end());
  ack.payload.insert(ack.payload.end(), this->identity_.session_id.begin(), this->identity_.session_id.end());
  return QueuedTx{TxSource::CONTROLLER, ack};
}

QueuedTx CtController::make_token_offer_response_(const CtFrame &token_offer) const {
  CtFrame response;
  response.destination_address = token_offer.source_address;
  response.source_address = this->identity_.address;
  response.subnet = this->identity_.subnet;
  response.send_method = token_offer.send_method;
  response.send_parameters = token_offer.send_parameters;
  response.source_node_type = this->identity_.node_type;
  response.message_type = CT_MSG_TYPE_TOKEN_OFFER_RESPONSE;
  response.packet_number = token_offer.packet_number;
  response.payload.reserve(18);
  response.payload.push_back(this->identity_.address);
  response.payload.push_back(this->identity_.subnet);
  response.payload.insert(response.payload.end(), this->identity_.mac_address.begin(), this->identity_.mac_address.end());
  response.payload.insert(response.payload.end(), this->identity_.session_id.begin(), this->identity_.session_id.end());
  return QueuedTx{TxSource::CONTROLLER, response};
}

ControllerStepResult CtController::try_send_now_(const QueuedTx &queued_tx) {
  ControllerStepResult out;
  ControllerTxAttempt attempt;
  attempt.source = queued_tx.source;
  attempt.bytes = CtFrameCodec::encode_frame(queued_tx.frame);
  out.tx_attempts.push_back(attempt);
  this->counters_.tx_attempted++;
  this->counters_.tx_success++;
  this->last_tx_ms_ = this->last_rx_ms_;
  return out;
}

ControllerStepResult CtController::send_next_queued_(TxSource fallback_source) {
  if (this->tx_queue_.empty()) {
    return ControllerStepResult{};
  }
  auto next_it = this->tx_queue_.begin();
  for (auto it = this->tx_queue_.begin(); it != this->tx_queue_.end(); ++it) {
    if (is_response_message_type(it->frame.message_type)) {
      next_it = it;
      break;
    }
  }
  QueuedTx next = *next_it;
  this->tx_queue_.erase(next_it);
  if (next.frame.payload.empty() && next.source == TxSource::CONTROLLER) {
    next.source = fallback_source;
  }
  return this->try_send_now_(next);
}

}  // namespace radish
}  // namespace esphome
