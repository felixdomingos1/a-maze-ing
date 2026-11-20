"""Terminal (ASCII + ANSI colours) rendering of a maze."""

from __future__ import annotations

from typing import List, Set, Tuple

from mazegen import EAST, SOUTH, Coord, MazeGenerator

RESET: str = "\033[0m"

# (name, ANSI background code) - background colours give solid blocks.
COLOURS: Tuple[Tuple[str, str], ...] = (
    ("white", "\033[47m"),
    ("blue", "\033[44m"),
    ("green", "\033[42m"),
    ("yellow", "\033[43m"),
    ("red", "\033[41m"),
    ("magenta", "\033[45m"),
    ("cyan", "\033[46m"),
)
ENTRY_COLOUR: str = "\033[45m"      # magenta
EXIT_COLOUR: str = "\033[41m"       # red
PATH_COLOUR: str = "\033[46m"       # cyan
EMPTY: str = "  "                   # one logical "pixel" = 2 characters


class Renderer:
    """Draw a :class:`MazeGenerator` in the terminal.

    The maze is drawn on a ``(2*height+1) x (2*width+1)`` character grid:
    odd/odd positions are cells, the positions between them are walls and
    even/even positions are the wall corners ("posts").

    Attributes:
        wall_index: Index in ``COLOURS`` of the wall colour.
        pattern_index: Index in ``COLOURS`` of the "42" colour.
        show_path: Whether the shortest path is displayed.
    """

    def __init__(self) -> None:
        """Start with white walls, a yellow "42" and the path hidden."""
        self.wall_index: int = 0
        self.pattern_index: int = 3
        self.show_path: bool = False

    def next_wall_colour(self) -> str:
        """Cycle to the next wall colour and return its name."""
        self.wall_index = (self.wall_index + 1) % len(COLOURS)
        return COLOURS[self.wall_index][0]

    def next_pattern_colour(self) -> str:
        """Cycle to the next "42" colour and return its name."""
        self.pattern_index = (self.pattern_index + 1) % len(COLOURS)
        return COLOURS[self.pattern_index][0]

    def render(self, maze: MazeGenerator) -> str:
        """Return the coloured picture of *maze* as a string."""
        wall = COLOURS[self.wall_index][1] + EMPTY + RESET
        pattern = COLOURS[self.pattern_index][1] + EMPTY + RESET
        path_cells: Set[Coord] = set()
        if self.show_path:
            path_cells = set(maze.solution_cells())
        lines: List[str] = []
        for row in range(2 * maze.height + 1):
            parts: List[str] = []
            for col in range(2 * maze.width + 1):
                parts.append(self._pixel(maze, row, col, wall, pattern,
                                         path_cells))
            lines.append("".join(parts))
        return "\n".join(lines)

    def _pixel(self, maze: MazeGenerator, row: int, col: int, wall: str,
               pattern: str, path: Set[Coord]) -> str:
        """Return the 2-character block drawn at ``(row, col)``."""
        x, y = col // 2, row // 2
        if row % 2 == 1 and col % 2 == 1:            # a cell
            return self._cell(maze, (x, y), pattern, path)
        if row % 2 == 1:                             # vertical wall
            return self._between(maze, (x - 1, y), EAST, (x, y), wall,
                                 pattern, path)
        if col % 2 == 1:                             # horizontal wall
            return self._between(maze, (x, y - 1), SOUTH, (x, y), wall,
                                 pattern, path)
        around = {(x - 1, y - 1), (x, y - 1), (x - 1, y), (x, y)}
        if around <= maze.pattern_cells:
            return pattern                           # post inside the "42"
        return wall if self._post_needed(maze, x, y) else EMPTY

    def _cell(self, maze: MazeGenerator, cell: Coord, pattern: str,
              path: Set[Coord]) -> str:
        """Colour of a cell: entry, exit, "42", path or empty."""
        if cell == maze.entry:
            return ENTRY_COLOUR + EMPTY + RESET
        if cell == maze.exit:
            return EXIT_COLOUR + EMPTY + RESET
        if cell in maze.pattern_cells:
            return pattern
        if cell in path:
            return PATH_COLOUR + EMPTY + RESET
        return EMPTY

    def _between(self, maze: MazeGenerator, first: Coord, wall_bit: int,
                 second: Coord, wall: str, pattern: str,
                 path: Set[Coord]) -> str:
        """Colour of the segment between two cells (or a border)."""
        a_in = maze.in_bounds(*first)
        b_in = maze.in_bounds(*second)
        if not (a_in and b_in):
            return wall                              # outer border
        if maze.has_wall(first[0], first[1], wall_bit):
            if (first in maze.pattern_cells
                    and second in maze.pattern_cells):
                return pattern                       # inside the "42"
            return wall
        if first in path and second in path:
            return PATH_COLOUR + EMPTY + RESET
        return EMPTY

    def _post_needed(self, maze: MazeGenerator, x: int, y: int) -> bool:
        """A corner post is drawn if any wall segment touches it.

        The post at ``(x, y)`` is the top-left corner of cell ``(x, y)``.
        """
        if x in (0, maze.width) or y in (0, maze.height):
            return True
        return (maze.has_wall(x - 1, y - 1, EAST)      # segment above
                or maze.has_wall(x - 1, y, EAST)       # segment below
                or maze.has_wall(x - 1, y - 1, SOUTH)  # segment left
                or maze.has_wall(x, y - 1, SOUTH))     # segment right
