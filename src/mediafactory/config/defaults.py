"""Default configuration constants for MediaFactory.

This module contains all default values and constants used throughout
the configuration system.
"""

import sys
from enum import Enum
from pathlib import Path

# Configuration file names
DEFAULT_CONFIG_FILE = "config.toml"
CONFIG_FILE_BACKUP_SUFFIX = ".backup"

# Environment variable prefix
ENV_PREFIX = "MF_"

# Default paths
DEFAULT_MODELS_PATH = Path("./models")
DEFAULT_CACHE_PATH = Path("./cache")
DEFAULT_LOG_PATH = Path("./logs")

# Model download sources
DEFAULT_DOWNLOAD_SOURCE = (
    "https://hf-mirror.com"  # Default to China mirror for better speed
)
CHINA_MIRROR_SOURCE = "https://hf-mirror.com"
OFFICIAL_SOURCE = "https://huggingface.co"

# Model download timeout (seconds)
# HTTP request timeout for huggingface_hub downloads
DEFAULT_MODEL_DOWNLOAD_TIMEOUT = 30  # 30 seconds for each HTTP request

# Whisper defaults
DEFAULT_WHISPER_BEAM_SIZE = 5
DEFAULT_WHISPER_PATIENCE = 1.0
DEFAULT_WHISPER_LENGTH_PENALTY = 1.0
DEFAULT_WHISPER_NO_SPEECH_THRESHOLD = 0.1
DEFAULT_WHISPER_CONDITION_ON_PREVIOUS_TEXT = False
DEFAULT_WHISPER_WORD_TIMESTAMPS = True

# Whisper VAD (Voice Activity Detection) defaults
# VAD filters out non-speech segments, reducing hallucinations in silence
DEFAULT_WHISPER_VAD_FILTER = True
DEFAULT_WHISPER_VAD_THRESHOLD = (
    0.35  # 降低阈值提高语音检测敏感度，改善分段效果 (0.0-1.0, higher = less speech detected)
)
DEFAULT_WHISPER_VAD_MIN_SPEECH_DURATION_MS = 250  # Minimum speech segment length
DEFAULT_WHISPER_VAD_MIN_SILENCE_DURATION_MS = 100  # Minimum silence for split
DEFAULT_WHISPER_VAD_SPEECH_PAD_MS = 30  # Padding around speech segments

# LLM API defaults
DEFAULT_LLM_TIMEOUT = 30
DEFAULT_LLM_MAX_RETRIES = 3
DEFAULT_LLM_RATE_LIMIT_ENABLED = True
DEFAULT_LLM_RATE_LIMIT_PER_SECOND = 5.0
DEFAULT_LLM_MAX_CHARS_PER_REQUEST = 3000
DEFAULT_LLM_MAX_SEGMENTS_PER_REQUEST = 100

# OpenAI Compatible defaults (统一的 LLM 后端)
DEFAULT_OPENAI_COMPATIBLE_PRESET = "openai"
DEFAULT_OPENAI_COMPATIBLE_MODEL = "gpt-4o-mini"
DEFAULT_OPENAI_COMPATIBLE_BASE_URL = "https://api.openai.com/v1"


# Backend names
class Backend(str, Enum):
    """Supported LLM backend identifiers."""

    OPENAI_COMPATIBLE = "openai_compatible"


# Language codes
class Language(str, Enum):
    """Commonly used language codes."""

    ENGLISH = "en"
    CHINESE = "zh"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    JAPANESE = "ja"
    KOREAN = "ko"
    RUSSIAN = "ru"
    PORTUGUESE = "pt"
    ITALIAN = "it"


# Validation constraints
class ValidationConstraints:
    """Validation constraints for configuration values."""

    # Whisper
    WHISPER_BEAM_SIZE_MIN = 1
    WHISPER_BEAM_SIZE_MAX = 10
    WHISPER_PATIENCE_MIN = 0.0
    WHISPER_PATIENCE_MAX = 10.0
    WHISPER_NO_SPEECH_THRESHOLD_MIN = 0.0
    WHISPER_NO_SPEECH_THRESHOLD_MAX = 1.0

    # Whisper VAD
    WHISPER_VAD_THRESHOLD_MIN = 0.0
    WHISPER_VAD_THRESHOLD_MAX = 1.0
    WHISPER_VAD_MIN_SPEECH_DURATION_MS_MIN = 0
    WHISPER_VAD_MIN_SPEECH_DURATION_MS_MAX = 10000
    WHISPER_VAD_MIN_SILENCE_DURATION_MS_MIN = 0
    WHISPER_VAD_MIN_SILENCE_DURATION_MS_MAX = 10000
    WHISPER_VAD_SPEECH_PAD_MS_MIN = 0
    WHISPER_VAD_SPEECH_PAD_MS_MAX = 1000

    # LLM API
    LLM_TIMEOUT_MIN = 1
    LLM_TIMEOUT_MAX = 300
    LLM_MAX_RETRIES_MIN = 0
    LLM_MAX_RETRIES_MAX = 10

    # Model download
    MODEL_DOWNLOAD_TIMEOUT_MIN = 10
    MODEL_DOWNLOAD_TIMEOUT_MAX = 600
    LLM_RATE_LIMIT_MIN = 0.0
    LLM_RATE_LIMIT_MAX = 100.0
    LLM_MAX_CHARS_MIN = 1
    LLM_MAX_CHARS_MAX = 100000
    LLM_MAX_SEGMENTS_MIN = 1
    LLM_MAX_SEGMENTS_MAX = 1000


def get_default_config_path() -> Path:
    """Get the default configuration file path.

    Returns:
        Path to config.toml in the application root.
    """
    return Path.cwd() / DEFAULT_CONFIG_FILE


def get_models_path() -> Path:
    """Get the default models directory path.

    Returns:
        Path to the models directory.
    """
    return DEFAULT_MODELS_PATH


def get_app_root_dir() -> Path:
    """Get application root directory.

    In PyInstaller packaged environment, returns the executable's directory.
    In development environment, returns the project root directory.

    Returns:
        Application root directory path
    """
    if getattr(sys, "frozen", False):
        # PyInstaller packaged environment
        if hasattr(sys, "_MEIPASS"):
            # --onefile mode
            return Path(sys.executable).parent
        else:
            # --onedir mode
            return Path(sys.executable).parent
    else:
        # Development environment - use the config package's parent's parent's parent
        # src/mediafactory/config -> src/mediafactory -> src -> project root
        return Path(__file__).parent.parent.parent.parent.resolve()


def get_config_path() -> Path:
    """Get the configuration file path.

    Returns:
        Path to config.toml in the application root.
    """
    return get_app_root_dir() / DEFAULT_CONFIG_FILE
