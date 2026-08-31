#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

#include "ct_types.h"

namespace esphome {
namespace radish {

struct CtParseResult {
  std::vector<CtFrame> frames{};
  uint32_t checksum_failures{0};
  uint32_t truncated_frames{0};
};

class CtFrameCodec {
 public:
  static CtParseResult parse_frames(const std::vector<uint8_t> &bytes);
  static std::vector<uint8_t> encode_frame(const CtFrame &frame);
  static uint16_t compute_checksum(const std::vector<uint8_t> &frame_without_checksum);

 private:
  static bool try_decode_at(const std::vector<uint8_t> &bytes, size_t offset, CtFrame *out_frame, size_t *consumed,
                            bool *truncated, bool *bad_checksum);
};

}  // namespace radish
}  // namespace esphome
