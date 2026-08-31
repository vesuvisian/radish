#include "ct_services_subordinate.h"

#include <iterator>

#include "esphome/core/log.h"

namespace esphome {
namespace radish {

static const char *const TAG = "radish.subordinate";

void SubordinateService::setup_persistence() {
  static constexpr uint32_t kSharedDataPreferenceKeys[SHARED_DATA_SECTOR_COUNT] = {
      0x52414430U,  // "RAD0"
      0x52414431U,  // "RAD1"
      0x52414432U,  // "RAD2"
  };

  for (size_t i = 0; i < SHARED_DATA_SECTOR_COUNT; ++i) {
    this->shared_data_sector_preferences_[i] =
        global_preferences->make_preference<PersistedSharedDataSectorImage>(kSharedDataPreferenceKeys[i], true);
    this->load_shared_data_sector_(i);
  }
  this->persistence_ready_ = true;
}

bool SubordinateService::is_application_message_type_(uint8_t message_type) {
  return message_type >= 0x01 && message_type <= 0xDA;
}

bool SubordinateService::handles_frame(const CtFrame &frame, const ControllerIdentity &identity) const {
  if (frame.destination_address != identity.address || frame.subnet != identity.subnet) {
    return false;
  }
  if (is_dataflow_packet(frame.packet_number)) {
    return false;
  }
  if (frame.message_type == CT_MSG_TYPE_R2R) {
    return false;
  }
  return is_application_message_type_(frame.message_type);
}

QueuedTx SubordinateService::build_set_network_node_list_response_(const CtFrame &frame,
                                                                   const ControllerIdentity &identity) {
  CtFrame response = frame;
  response.destination_address = frame.source_address;
  response.source_address = identity.address;
  response.subnet = identity.subnet;
  response.source_node_type = identity.node_type;
  response.message_type = CT_MSG_TYPE_SET_NETWORK_NODE_LIST_RESPONSE;
  response.payload = frame.payload;
  return QueuedTx{TxSource::CONTROLLER, response};
}

QueuedTx SubordinateService::build_network_shared_data_sector_response_(const CtFrame &frame,
                                                                        const ControllerIdentity &identity,
                                                                        const std::vector<uint8_t> &payload) {
  CtFrame response = frame;
  response.destination_address = frame.source_address;
  response.source_address = identity.address;
  response.subnet = identity.subnet;
  response.source_node_type = identity.node_type;
  response.message_type = CT_MSG_TYPE_NETWORK_SHARED_DATA_SECTOR_RESPONSE;
  response.payload = payload;
  return QueuedTx{TxSource::CONTROLLER, response};
}

std::optional<size_t> SubordinateService::shared_data_sector_index_for_node_type_(uint8_t node_type) {
  if (node_type == 1 || node_type == 21) {
    return 0;
  }
  if (node_type == 2 || node_type == 3) {
    return 1;
  }
  if (node_type == 4 || node_type == 5 || node_type == 12) {
    return 2;
  }
  return std::nullopt;
}

bool SubordinateService::should_accept_shared_data_write_(size_t sector_index, uint8_t incoming_node_type) const {
  // Sector 0 gives Node Type 21 (Zone Controller) overwrite priority over Node Type 1 (Thermostat).
  if (sector_index == 0) {
    const SharedDataSectorImage &sector = this->shared_data_sectors_[0];
    if (sector.valid && sector.node_type == 21 && incoming_node_type == 1) {
      return false;
    }
  }
  return true;
}

std::vector<uint8_t> SubordinateService::make_shared_data_response_payload_(uint8_t requested_node_type) const {
  const std::optional<size_t> sector_index = shared_data_sector_index_for_node_type_(requested_node_type);
  if (!sector_index.has_value()) {
    return {};
  }
  const SharedDataSectorImage &sector = this->shared_data_sectors_[sector_index.value()];
  if (!sector.valid) {
    return {};
  }
  std::vector<uint8_t> payload;
  payload.reserve(1 + sector.data.size());
  payload.push_back(sector.node_type);
  payload.insert(payload.end(), sector.data.begin(), sector.data.end());
  return payload;
}

void SubordinateService::persist_shared_data_sector_(size_t sector_index) {
  if (!this->persistence_ready_ || sector_index >= SHARED_DATA_SECTOR_COUNT) {
    return;
  }

  PersistedSharedDataSectorImage stored{};
  const SharedDataSectorImage &sector = this->shared_data_sectors_[sector_index];
  stored.valid = sector.valid ? 1 : 0;
  stored.node_type = sector.node_type;
  const size_t bounded_len = sector.data.size() > SHARED_DATA_MAX_BYTES ? SHARED_DATA_MAX_BYTES : sector.data.size();
  stored.length = static_cast<uint16_t>(bounded_len);
  for (size_t i = 0; i < bounded_len; ++i) {
    stored.data[i] = sector.data[i];
  }
  this->shared_data_sector_preferences_[sector_index].save(&stored);
}

void SubordinateService::load_shared_data_sector_(size_t sector_index) {
  if (sector_index >= SHARED_DATA_SECTOR_COUNT) {
    return;
  }

  PersistedSharedDataSectorImage stored{};
  if (!this->shared_data_sector_preferences_[sector_index].load(&stored)) {
    return;
  }
  SharedDataSectorImage &sector = this->shared_data_sectors_[sector_index];
  sector.valid = stored.valid != 0;
  sector.node_type = stored.node_type;
  const size_t bounded_len = stored.length > SHARED_DATA_MAX_BYTES ? SHARED_DATA_MAX_BYTES : stored.length;
  sector.data.assign(stored.data, stored.data + bounded_len);
  ESP_LOGD(TAG, "Loaded shared-data sector %u (valid=%s, node_type=%u, len=%u)", static_cast<unsigned>(sector_index),
           sector.valid ? "yes" : "no", static_cast<unsigned>(sector.node_type), static_cast<unsigned>(bounded_len));
}

ServiceOutput SubordinateService::on_frame(const CtFrame &frame, const ControllerIdentity &identity) {
  ServiceOutput output;
  if (!this->handles_frame(frame, identity)) {
    return output;
  }
  if (frame.message_type == CT_MSG_TYPE_SET_NETWORK_NODE_LIST_REQUEST) {
    output.queued.push_back(build_set_network_node_list_response_(frame, identity));
    return output;
  }
  if (frame.message_type == CT_MSG_TYPE_NETWORK_SHARED_DATA_SECTOR_REQUEST) {
    if (frame.payload.empty()) {
      output.queued.push_back(build_network_shared_data_sector_response_(frame, identity, {}));
      return output;
    }

    const uint8_t operation_and_node_type = frame.payload[0];
    const bool is_read = (operation_and_node_type & 0x80U) != 0;
    const uint8_t requested_node_type = static_cast<uint8_t>(operation_and_node_type & 0x7FU);
    const std::optional<size_t> sector_index = shared_data_sector_index_for_node_type_(requested_node_type);

    if (!is_read && sector_index.has_value() &&
        this->should_accept_shared_data_write_(sector_index.value(), requested_node_type)) {
      SharedDataSectorImage &sector = this->shared_data_sectors_[sector_index.value()];
      const std::vector<uint8_t> incoming_data(std::next(frame.payload.begin()), frame.payload.end());
      const bool changed = !sector.valid || sector.node_type != requested_node_type || sector.data != incoming_data;
      sector.valid = true;
      sector.node_type = requested_node_type;
      sector.data = incoming_data;
      if (changed) {
        this->persist_shared_data_sector_(sector_index.value());
      }
    }

    output.queued.push_back(
        build_network_shared_data_sector_response_(frame, identity, this->make_shared_data_response_payload_(requested_node_type)));
    return output;
  }

  // Application message space is intentionally routed here for subordinate
  // application-specific behavior expansion.
  return output;
}

}  // namespace radish
}  // namespace esphome
