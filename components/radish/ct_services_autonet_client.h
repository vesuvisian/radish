#pragma once

#include "ct_types.h"

namespace esphome {
namespace radish {

class AutoNetClient {
 public:
  void set_config(const AutoNetConfig &config) { this->config_ = config; }
  ServiceOutput force_unaddressed();
  ServiceOutput on_frame(const CtFrame &frame, const ControllerIdentity &identity, uint32_t now_ms);
  ServiceOutput on_tick(const ControllerIdentity &identity, uint32_t now_ms);
  AutoNetClientState state() const { return this->state_; }

 private:
  std::vector<uint8_t> generate_session_id_(const ControllerIdentity &identity, uint32_t now_ms);
  uint32_t compute_slot_delay_ms_(const CtFrame &frame, const ControllerIdentity &identity);
  void enter_unaddressed_(ServiceOutput *output);
  bool validate_or_capture_r2r_coordinator_(const CtFrame &frame, const ControllerIdentity &identity, ServiceOutput *output);
  bool is_address_confirmation_valid_(const CtFrame &frame, const ControllerIdentity &identity) const;
  static bool is_node_discovery_for_this_type_(const CtFrame &frame, uint8_t local_node_type);
  static bool is_set_address_for_this_identity_(const CtFrame &frame, const ControllerIdentity &identity);
  static bool is_get_node_id_for_this_identity_(const CtFrame &frame, const ControllerIdentity &identity);
  static QueuedTx build_node_discovery_response_(const CtFrame &frame, const ControllerIdentity &identity);
  static QueuedTx build_address_confirmation_response_(const CtFrame &frame, const ControllerIdentity &identity);
  static QueuedTx build_set_address_response_(const CtFrame &frame, const ControllerIdentity &identity,
                                              uint8_t assigned_address, uint8_t assigned_subnet);
  static QueuedTx build_get_node_id_response_(const CtFrame &frame, const ControllerIdentity &identity);

  AutoNetConfig config_{};
  AutoNetClientState state_{AutoNetClientState::UNADDRESSED};
  uint32_t slot_delay_due_ms_{0};
  uint32_t last_address_confirmation_ms_{0};
  bool pending_address_confirmation_response_{false};
  uint32_t pending_address_confirmation_due_ms_{0};
  CtFrame pending_address_confirmation_frame_{};
  uint32_t sequence_counter_{0};
  CtFrame pending_discovery_request_{};
  std::vector<uint8_t> expected_r2r_coordinator_mac_{};
  std::vector<uint8_t> expected_r2r_coordinator_session_{};
};

}  // namespace radish
}  // namespace esphome
