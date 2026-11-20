"""Parsing and validation of the KEY=VALUE configuration file."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

MANDATORY_KEYS: Tuple[str, ...] = (
    "WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT",
)
OPTIONAL_KEYS: Tuple[str, ...] = ("SEED", "ALGORITHM")
MAX_SIZE: int = 1000


class ConfigError(Exception):
    """Raised when the configuration file is missing or invalid."""


@dataclass
class Config:
    """Validated configuration values.

    Attributes:
        width: Maze width in cells.
        height: Maze height in cells.
        entry: Entry coordinates ``(x, y)``.
        exit: Exit coordinates ``(x, y)``.
        output_file: Path of the file the maze is written to.
        perfect: Whether the maze must be perfect.
        seed: Optional random seed.
        algorithm: Carving algorithm name.
    """

    width: int
    height: int
    entry: Tuple[int, int]
    exit: Tuple[int, int]
    output_file: str
    perfect: bool
    seed: Optional[int] = None
    algorithm: str = "backtracker"


def read_pairs(path: str) -> Dict[str, str]:
    """Read the raw KEY=VALUE pairs of a configuration file.

    Args:
        path: Path to the configuration file.

    Returns:
        A dictionary mapping upper-case keys to their (stripped) values.

    Raises:
        ConfigError: If the file cannot be read or a line is malformed.
    """
    pairs: Dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as stream:
            for number, raw in enumerate(stream, start=1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    raise ConfigError(
                        f"line {number}: expected KEY=VALUE, got '{line}'.")
                key, value = (part.strip() for part in line.split("=", 1))
                key = key.upper()
                if not key:
                    raise ConfigError(f"line {number}: empty key.")
                if key in pairs:
                    raise ConfigError(
                        f"line {number}: key '{key}' is defined twice.")
                pairs[key] = value
    except FileNotFoundError:
        raise ConfigError(f"configuration file not found: '{path}'.")
    except IsADirectoryError:
        raise ConfigError(f"'{path}' is a directory, not a file.")
    except PermissionError:
        raise ConfigError(f"permission denied when reading '{path}'.")
    except UnicodeDecodeError:
        raise ConfigError(f"'{path}' is not a valid UTF-8 text file.")
    except OSError as error:
        raise ConfigError(f"cannot read '{path}': {error.strerror}.")
    return pairs


def _parse_int(key: str, value: str) -> int:
    """Convert *value* to an int or raise a clear ConfigError."""
    try:
        return int(value)
    except ValueError:
        raise ConfigError(f"{key} must be an integer, got '{value}'.")


def _parse_size(key: str, value: str) -> int:
    """Parse WIDTH/HEIGHT: an integer between 1 and MAX_SIZE."""
    size = _parse_int(key, value)
    if not 1 <= size <= MAX_SIZE:
        raise ConfigError(f"{key} must be between 1 and {MAX_SIZE}, "
                          f"got {size}.")
    return size


def _parse_coord(key: str, value: str) -> Tuple[int, int]:
    """Parse an ``x,y`` pair."""
    parts = value.split(",")
    if len(parts) != 2:
        raise ConfigError(f"{key} must be written x,y (e.g. 0,0), "
                          f"got '{value}'.")
    return _parse_int(key, parts[0].strip()), _parse_int(key,
                                                         parts[1].strip())


def _parse_bool(key: str, value: str) -> bool:
    """Parse True/False (case-insensitive, also accepts 1/0, yes/no)."""
    lowered = value.lower()
    if lowered in ("true", "1", "yes"):
        return True
    if lowered in ("false", "0", "no"):
        return False
    raise ConfigError(f"{key} must be True or False, got '{value}'.")


def load_config(path: str) -> Config:
    """Read and validate the configuration file.

    Args:
        path: Path to the configuration file.

    Returns:
        The validated :class:`Config`.

    Raises:
        ConfigError: On any missing, unknown or invalid value.
    """
    pairs = read_pairs(path)
    missing = [key for key in MANDATORY_KEYS if key not in pairs]
    if missing:
        raise ConfigError(f"missing mandatory key(s): {', '.join(missing)}.")
    unknown = [key for key in pairs
               if key not in MANDATORY_KEYS + OPTIONAL_KEYS]
    if unknown:
        raise ConfigError(f"unknown key(s): {', '.join(unknown)}.")
    output_file = pairs["OUTPUT_FILE"]
    if not output_file:
        raise ConfigError("OUTPUT_FILE cannot be empty.")
    seed: Optional[int] = None
    if pairs.get("SEED", ""):
        seed = _parse_int("SEED", pairs["SEED"])
    return Config(
        width=_parse_size("WIDTH", pairs["WIDTH"]),
        height=_parse_size("HEIGHT", pairs["HEIGHT"]),
        entry=_parse_coord("ENTRY", pairs["ENTRY"]),
        exit=_parse_coord("EXIT", pairs["EXIT"]),
        output_file=output_file,
        perfect=_parse_bool("PERFECT", pairs["PERFECT"]),
        seed=seed,
        algorithm=pairs.get("ALGORITHM", "backtracker").lower()
        or "backtracker",
    )
