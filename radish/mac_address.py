import uuid

from radish.utils import tabulate


class MacAddress(bytearray):
    @classmethod
    def create(cls, manufacturer_id=b"\x00\x00", unit_id=None):
        self = cls(8)
        self.manufacturer_id = manufacturer_id
        if unit_id is None:
            unit_id = uuid.uuid4().bytes[:5]
        self.unit_id = unit_id
        return self

    @property
    def manufacturer_id(self):
        return bytes(self[1:3])

    @manufacturer_id.setter
    def manufacturer_id(self, value):
        if len(value) != 2:
            raise ValueError("manufacturer_id must be 2 bytes")
        self[1:3] = value

    @property
    def unit_id(self):
        return bytes(self[3:])

    @unit_id.setter
    def unit_id(self, value):
        if len(value) != 5:
            raise ValueError("unit_id must be 5 bytes")
        self[3:] = value

    def pretty_format(self, title=False):
        output = f"Manufacturer ID: {self.manufacturer_id.hex(':')}\nUnit ID: {self.unit_id.hex(':')}"
        if title:
            output = f"MAC Address:\n{tabulate(output)}"
        return output
