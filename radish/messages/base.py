"""Base message class for Daikin HVAC payloads."""

from typing import Any

from ..utils import tabulate


def parse_db_id_datagram(payload: bytes) -> tuple[list[dict[str, Any]], list[str]]:
    """Parse an MDI payload as repeated DB-ID records.

    Record format:
    - 1 byte DB ID tag
    - 1 byte DB length
    - N bytes of value
    """
    records: list[dict[str, Any]] = []
    warnings: list[str] = []
    i = 0

    while i < len(payload):
        if i + 2 > len(payload):
            warnings.append(
                f"Truncated record header at offset {i}: "
                f"{len(payload) - i} byte(s) remain"
            )
            break

        db_id = payload[i]
        db_len = payload[i + 1]
        value_start = i + 2
        value_end = value_start + db_len

        if value_end > len(payload):
            available = len(payload) - value_start
            warnings.append(
                f"Truncated record value for DB ID 0x{db_id:02x} at offset {i}: "
                f"declared {db_len} byte(s), only {max(available, 0)} available"
            )
            break

        records.append(
            {
                "db_id": db_id,
                "db_len": db_len,
                "value": payload[value_start:value_end],
            }
        )
        i = value_end

    return records, warnings


class Message:
    def __init__(self, data=None):
        self.data = data

    @property
    def name(self):
        return self.__class__.__name__

    @classmethod
    def from_bytes(cls, data):
        return cls(data)

    def __repr__(self):
        return f"{self.name}: {self.data.hex(':')}"

    def pretty_format(self, title=False):
        output = self._format_output()
        if title:
            output = f"{self.name}:\n{tabulate(output)}"
        return output

    def _format_output(self):
        return f"{self.data.hex(':')}"


class NoPayloadMessage(Message):
    """Message type with a required empty payload."""

    def _format_output(self):
        if not self.data:
            return "No payload"
        return f"Unexpected payload for {self.name}: {self.data.hex(':')}"
