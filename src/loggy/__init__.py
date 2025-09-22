from .logger import Logger
from .event import Event


logger = Logger()
event = Event()

info = logger.info
debug = logger.debug
warning = logger.warning
error = logger.error
critical = logger.critical
