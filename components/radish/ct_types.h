#pragma once

#include <cstdint>
#include <optional>
#include <vector>

namespace esphome {
namespace radish {

constexpr uint8_t CT_MSG_TYPE_R2R = 0x00;
constexpr uint8_t CT_MSG_TYPE_TOKEN_OFFER = 0x77;
constexpr uint8_t CT_MSG_TYPE_TOKEN_OFFER_RESPONSE = 0xF7;
constexpr uint8_t CT_MSG_TYPE_ADDRESS_CONFIRMATION_PUSH = 0x76;
constexpr uint8_t CT_MSG_TYPE_ADDRESS_CONFIRMATION_RESPONSE = 0xF6;
constexpr uint8_t CT_MSG_TYPE_NODE_DISCOVERY_REQUEST = 0x79;
constexpr uint8_t CT_MSG_TYPE_NODE_DISCOVERY_RESPONSE = 0xF9;
constexpr uint8_t CT_MSG_TYPE_SET_ADDRESS_REQUEST = 0x7A;
constexpr uint8_t CT_MSG_TYPE_SET_ADDRESS_RESPONSE = 0xFA;
constexpr uint8_t CT_MSG_TYPE_GET_NODE_ID_REQUEST = 0x7B;
constexpr uint8_t CT_MSG_TYPE_GET_NODE_ID_RESPONSE = 0xFB;
constexpr uint8_t CT_MSG_TYPE_SET_NETWORK_NODE_LIST_REQUEST = 0x14;
constexpr uint8_t CT_MSG_TYPE_SET_NETWORK_NODE_LIST_RESPONSE = 0x94;
constexpr uint8_t CT_MSG_TYPE_NETWORK_SHARED_DATA_SECTOR_REQUEST = 0x7D;
constexpr uint8_t CT_MSG_TYPE_NETWORK_SHARED_DATA_SECTOR_RESPONSE = 0xFD;

constexpr uint8_t CT_R2R_CODE_REQUEST = 0x00;
constexpr uint8_t CT_R2R_CODE_ACK = 0x06;

constexpr uint8_t CT_ADDRESS_BROADCAST = 0x00;
constexpr uint8_t CT_SUBNET_BROADCAST = 0x00;
constexpr uint8_t CT_SUBNET_V2 = 0x03;

constexpr uint8_t CT_PACKET_FLAG_DATAFLOW = 0x80;
constexpr uint8_t CT_PACKET_FLAG_VERSION = 0x20;

inline bool is_dataflow_packet(uint8_t packet_number) {
  return (packet_number & CT_PACKET_FLAG_DATAFLOW) != 0;
}

struct CtFrame {
  uint8_t destination_address{0};
  uint8_t source_address{0};
  uint8_t subnet{0};
  uint8_t send_method{0};
  uint16_t send_parameters{0};
  uint8_t source_node_type{0};
  uint8_t message_type{0};
  uint8_t packet_number{0};
  std::vector<uint8_t> payload{};
  uint16_t checksum{0};
};

struct ControllerIdentity {
  uint8_t address{0};
  uint8_t subnet{CT_SUBNET_V2};
  uint8_t node_type{39};  // Temperature sensor
  std::vector<uint8_t> mac_address{0, 0, 0, 0, 0, 0, 0, 1};
  std::vector<uint8_t> session_id{0, 0, 0, 0, 0, 0, 0, 1};
};

enum class AutoNetClientState {
  UNADDRESSED,
  AWAITING_SLOT_DELAY_FOR_DISCOVERY_RESPONSE,
  AWAITING_SET_ADDRESS,
  ADDRESSED_ACTIVE,
  RELINQUISH_PENDING,
};

struct AutoNetConfig {
  bool enabled{true};
  uint32_t slot_delay_min_ms{100};
  uint32_t slot_delay_max_ms{2500};
  uint32_t keepalive_timeout_ms{120000};
  uint32_t deterministic_seed{0};
  bool deterministic_seed_set{false};
};

enum class TxSource {
  CONTROLLER,
  AUTONET_CLIENT,
};

struct QueuedTx {
  TxSource source{TxSource::CONTROLLER};
  CtFrame frame{};
};

struct ControllerCounters {
  uint32_t raw_chunks_seen{0};
  uint32_t raw_bytes_seen{0};
  uint32_t frames_valid{0};
  uint32_t frames_checksum_failed{0};
  uint32_t frames_truncated{0};
  uint32_t frames_filtered{0};
  uint32_t queue_dropped{0};
  uint32_t tx_attempted{0};
  uint32_t tx_success{0};
  uint32_t tx_failed{0};
};

struct ServiceOutput {
  std::vector<QueuedTx> queued{};
  std::optional<uint8_t> assigned_address{};
  std::optional<uint8_t> assigned_subnet{};
  std::optional<std::vector<uint8_t>> updated_session_id{};
  bool clear_assignment{false};
  bool saw_address_confirmation{false};
  AutoNetClientState autonet_state{AutoNetClientState::UNADDRESSED};
};

}  // namespace radish
}  // namespace esphome
