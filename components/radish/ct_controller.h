#pragma once

#include <cstddef>
#include <deque>
#include <string>
#include <vector>

#include "ct_services_autonet_client.h"
#include "ct_services_subordinate.h"
#include "ct_types.h"

namespace esphome {
namespace radish {

struct ControllerTxAttempt {
  TxSource source{TxSource::CONTROLLER};
  std::vector<uint8_t> bytes{};
};

struct ControllerStepResult {
  std::vector<ControllerTxAttempt> tx_attempts{};
  bool should_publish_raw{false};
};

class CtController {
 public:
  void setup() { this->subordinate_service_.setup_persistence(); }
  void set_enable_raw_mqtt_forwarding(bool enabled) { this->enable_raw_mqtt_forwarding_ = enabled; }
  void set_identity(const ControllerIdentity &identity) { this->identity_ = identity; }
  void set_max_tx_queue_depth(size_t max_tx_queue_depth) { this->max_tx_queue_depth_ = max_tx_queue_depth; }
  void set_slot_delay_ms(uint32_t slot_delay_ms) { this->slot_delay_ms_ = slot_delay_ms; }
  void set_autonet_config(const AutoNetConfig &config);

  ControllerStepResult on_raw_chunk(const std::vector<uint8_t> &raw_bytes, uint32_t now_ms);
  ControllerStepResult tick(uint32_t now_ms);
  bool enqueue_outbound(const QueuedTx &queued_tx);

  const ControllerCounters &counters() const { return this->counters_; }
  const ControllerIdentity &identity() const { return this->identity_; }

 private:
  ControllerStepResult handle_frame_(const CtFrame &frame, uint32_t now_ms);
  void append_service_outputs_(const ServiceOutput &service_output, ControllerStepResult *out);
  void maybe_reset_dataflow_cycle_(const CtFrame &frame, uint32_t now_ms);
  void clear_pending_tx_state_();
  bool is_for_local_node_(const CtFrame &frame) const;
  bool is_subnet3_token_offer_(const CtFrame &frame) const;

  QueuedTx make_r2r_ack_(const CtFrame &r2r) const;
  QueuedTx make_non_dataflow_ack_(const CtFrame &frame) const;
  QueuedTx make_token_offer_response_(const CtFrame &token_offer) const;
  ControllerStepResult try_send_now_(const QueuedTx &queued_tx);
  ControllerStepResult send_next_queued_(TxSource fallback_source);

  ControllerIdentity identity_{};
  ControllerCounters counters_{};
  AutoNetClient autonet_client_{};
  SubordinateService subordinate_service_{};

  std::deque<QueuedTx> tx_queue_{};
  size_t max_tx_queue_depth_{16};
  bool enable_raw_mqtt_forwarding_{true};

  uint32_t last_rx_ms_{0};
  uint32_t last_tx_ms_{0};
  uint64_t bus_epoch_{0};

  bool token_offer_sent_this_cycle_{false};
  uint32_t last_cycle_reset_ms_{0};
  uint32_t slot_delay_ms_{250};
  bool pending_token_offer_{false};
  uint32_t pending_token_due_ms_{0};
  uint64_t pending_token_epoch_{0};
  CtFrame pending_token_offer_frame_{};
  AutoNetConfig autonet_config_{};
};

}  // namespace radish
}  // namespace esphome
