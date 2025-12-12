import logging
from enum import Enum, auto

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ThreadMaster")

class ThreadPriority(Enum):
    """Thread priority levels"""
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    CRITICAL = auto()

class ThreadStatus(Enum):
    """Thread status states"""
    PENDING = auto()
    RUNNING = auto()
    WAITING = auto()
    COMPLETED = auto()
    FAILED = auto()
    TERMINATED = auto()

# Updated by Hasini

# Updated by Hasini
