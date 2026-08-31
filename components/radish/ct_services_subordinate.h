#pragma once

#include <array>
#include <cstddef>
#include <optional>

#include "ct_types.h"
#include "esphome/core/preferences.h"

namespace esphome {
namespace radish {

class SubordinateService {
 public:
  void setup_persistence();
  ServiceOutput on_frame(const CtFrame &frame, const ControllerIdentity &identity);
  bool handles_frame(const CtFrame &frame, const ControllerIdentity &identity) const;
  static bool is_application_message_type_(uint8_t message_type);
  static QueuedTx build_set_network_node_list_response_(const CtFrame &frame, const ControllerIdentity &identity);
  static QueuedTx build_network_shared_data_sector_response_(const CtFrame &frame, const ControllerIdentity &identity,
                                                             const std::vector<uint8_t> &payload);

 private:
  static constexpr size_t SHARED_DATA_MAX_BYTES = 200;
  static constexpr size_t SHARED_DATA_SECTOR_COUNT = 3;

  struct PersistedSharedDataSectorImage {
    uint8_t valid{0};
    uint8_t node_type{0};
    uint16_t length{0};
    uint8_t data[SHARED_DATA_MAX_BYTES]{};
  };

  struct SharedDataSectorImage {
    bool valid{false};
    uint8_t node_type{0};
    std::vector<uint8_t> data{};
  };

  static std::optional<size_t> shared_data_sector_index_for_node_type_(uint8_t node_type);
  bool should_accept_shared_data_write_(size_t sector_index, uint8_t incoming_node_type) const;
  std::vector<uint8_t> make_shared_data_response_payload_(uint8_t requested_node_type) const;
  void persist_shared_data_sector_(size_t sector_index);
  void load_shared_data_sector_(size_t sector_index);

  std::array<SharedDataSectorImage, SHARED_DATA_SECTOR_COUNT> shared_data_sectors_{};
  std::array<ESPPreferenceObject, SHARED_DATA_SECTOR_COUNT> shared_data_sector_preferences_{};
  bool persistence_ready_{false};
};

}  // namespace radish
}  // namespace esphome
