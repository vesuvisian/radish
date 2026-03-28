"""
Message registry and Daikin HVAC message implementations.

Importing this package registers all known message classes.
"""

from .base import Message
from .registry import MessageRegistry

# Import modules for side-effect registration.
from . import ct_485, ct_cim  # noqa: F401
from .ct_485 import *  # noqa: F403
from .ct_cim import *  # noqa: F403

__all__ = ["MessageRegistry", "Message", *ct_cim.__all__, *ct_485.__all__]
