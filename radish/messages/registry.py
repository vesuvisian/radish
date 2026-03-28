"""Message registry for Daikin HVAC message types."""


class MessageRegistry:
    _registry = {}

    @classmethod
    def register(cls, message_type):
        def decorator(subclass):
            cls._registry[message_type] = subclass
            return subclass

        return decorator

    @classmethod
    def get_message_class(cls, message_type):
        from .base import Message

        return cls._registry.get(message_type, Message)

    @classmethod
    def parse(cls, message_type, data):
        msg_cls = cls.get_message_class(message_type)
        return msg_cls.from_bytes(data)
