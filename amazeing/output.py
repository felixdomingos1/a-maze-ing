"""Writing the maze to the output file (hexadecimal format)."""

from __future__ import annotations

from mazegen import MazeGenerator


class OutputError(Exception):
    """Raised when the output file cannot be written."""


def format_maze(maze: MazeGenerator) -> str:
    """Return the full text of the output file.

    Format: one hexadecimal digit per cell, one row per line, then an
    empty line, the entry ``x,y``, the exit ``x,y`` and the shortest path.
    Every line ends with ``\\n``.

    Args:
        maze: A generated maze.

    Returns:
        The file content.
    """
    lines = maze.to_hex_lines()
    lines.append("")
    lines.append(f"{maze.entry[0]},{maze.entry[1]}")
    lines.append(f"{maze.exit[0]},{maze.exit[1]}")
    lines.append(maze.solve())
    return "\n".join(lines) + "\n"


def write_maze(maze: MazeGenerator, path: str) -> None:
    """Write *maze* to *path*.

    Args:
        maze: A generated maze.
        path: Destination file.

    Raises:
        OutputError: If the file cannot be written.
    """
    try:
        with open(path, "w", encoding="utf-8") as stream:
            stream.write(format_maze(maze))
    except IsADirectoryError:
        raise OutputError(f"OUTPUT_FILE '{path}' is a directory.")
    except PermissionError:
        raise OutputError(f"permission denied when writing '{path}'.")
    except OSError as error:
        raise OutputError(f"cannot write '{path}': {error.strerror}.")
