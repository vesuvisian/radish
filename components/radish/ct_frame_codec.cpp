#include "ct_frame_codec.h"

namespace esphome {
namespace radish {

uint16_t CtFrameCodec::compute_checksum(const std::vector<uint8_t> &frame_without_checksum) {
  uint16_t sum1 = 0xAA;
  uint16_t sum2 = 0x00;
  for (uint8_t byte : frame_without_checksum) {
    sum1 = static_cast<uint16_t>((sum1 + byte) % 255U);
    sum2 = static_cast<uint16_t>((sum2 + sum1) % 255U);
  }
  const uint8_t crc_low = static_cast<uint8_t>(255U - ((sum1 + sum2) % 255U));
  const uint8_t crc_high = static_cast<uint8_t>(255U - ((sum1 + crc_low) % 255U));
  return static_cast<uint16_t>((static_cast<uint16_t>(crc_high) << 8) | static_cast<uint16_t>(crc_low));
}

std::vector<uint8_t> CtFrameCodec::encode_frame(const CtFrame &frame) {
  std::vector<uint8_t> out;
  out.reserve(12 + frame.payload.size());
  out.push_back(frame.destination_address);
  out.push_back(frame.source_address);
  out.push_back(frame.subnet);
  out.push_back(frame.send_method);
  out.push_back(static_cast<uint8_t>(frame.send_parameters & 0xFF));
  out.push_back(static_cast<uint8_t>((frame.send_parameters >> 8) & 0xFF));
  out.push_back(frame.source_node_type);
  out.push_back(frame.message_type);
  out.push_back(frame.packet_number);
  out.push_back(static_cast<uint8_t>(frame.payload.size()));
  out.insert(out.end(), frame.payload.begin(), frame.payload.end());

  const uint16_t checksum = compute_checksum(out);
  out.push_back(static_cast<uint8_t>(checksum & 0xFF));
  out.push_back(static_cast<uint8_t>((checksum >> 8) & 0xFF));
  return out;
}

bool CtFrameCodec::try_decode_at(const std::vector<uint8_t> &bytes, size_t offset, CtFrame *out_frame, size_t *consumed,
                                 bool *truncated, bool *bad_checksum) {
  *truncated = false;
  *bad_checksum = false;
  if (bytes.size() < offset + 12) {
    *truncated = true;
    return false;
  }

  const uint8_t packet_length = bytes[offset + 9];
  const size_t frame_len = 10 + static_cast<size_t>(packet_length) + 2;
  if (bytes.size() < offset + frame_len) {
    *truncated = true;
    return false;
  }

  CtFrame frame;
  frame.destination_address = bytes[offset + 0];
  frame.source_address = bytes[offset + 1];
  frame.subnet = bytes[offset + 2];
  frame.send_method = bytes[offset + 3];
  frame.send_parameters = static_cast<uint16_t>(bytes[offset + 4]) |
                          (static_cast<uint16_t>(bytes[offset + 5]) << 8);
  frame.source_node_type = bytes[offset + 6];
  frame.message_type = bytes[offset + 7];
  frame.packet_number = bytes[offset + 8];
  frame.payload.assign(bytes.begin() + static_cast<long>(offset + 10),
                       bytes.begin() + static_cast<long>(offset + 10 + packet_length));
  frame.checksum = static_cast<uint16_t>(bytes[offset + frame_len - 2]) |
                   (static_cast<uint16_t>(bytes[offset + frame_len - 1]) << 8);

  std::vector<uint8_t> body(bytes.begin() + static_cast<long>(offset),
                            bytes.begin() + static_cast<long>(offset + frame_len - 2));
  const uint16_t expected_checksum = compute_checksum(body);
  if (expected_checksum != frame.checksum) {
    *bad_checksum = true;
    return false;
  }

  *out_frame = frame;
  *consumed = frame_len;
  return true;
}

CtParseResult CtFrameCodec::parse_frames(const std::vector<uint8_t> &bytes) {
  CtParseResult result;
  size_t offset = 0;
  while (offset < bytes.size()) {
    CtFrame decoded;
    size_t consumed = 0;
    bool truncated = false;
    bool bad_checksum = false;
    if (try_decode_at(bytes, offset, &decoded, &consumed, &truncated, &bad_checksum)) {
      result.frames.push_back(decoded);
      offset += consumed;
      continue;
    }
    if (truncated) {
      result.truncated_frames++;
      break;
    }
    if (bad_checksum) {
      result.checksum_failures++;
    }
    offset += 1;
  }
  return result;
}

}  // namespace radish
}  // namespace esphome
