from .logger import Logger
from .event import Event
from .api import config as config_module


logger = Logger()
event = Event()
config = config_module

info = logger.info
debug = logger.debug
warning = logger.warning
error = logger.error
critical = logger.critical
