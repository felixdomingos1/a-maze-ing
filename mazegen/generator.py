"""Reusable maze generator.

The whole generation logic lives in the :class:`MazeGenerator` class so it can
be imported by any later project::

    from mazegen import MazeGenerator

    gen = MazeGenerator(width=20, height=15, entry=(0, 0), exit=(19, 14),
                        perfect=True, seed=42)
    gen.generate()
    print(gen.grid[0][0])          # wall bitmask of the top-left cell
    print(gen.solve())             # shortest path, e.g. "EESSWS..."

Wall encoding: one integer per cell, a set bit means the wall is *closed*:
bit 0 = North, bit 1 = East, bit 2 = South, bit 3 = West.
"""

from __future__ import annotations

import random
from collections import deque
from typing import Dict, List, Optional, Set, Tuple

Coord = Tuple[int, int]
"""A cell position as ``(x, y)``: x is the column, y is the row."""

NORTH: int = 1
EAST: int = 2
SOUTH: int = 4
WEST: int = 8
ALL_WALLS: int = NORTH | EAST | SOUTH | WEST

DIRECTIONS: Dict[int, Tuple[int, int, str]] = {
    NORTH: (0, -1, "N"),
    EAST: (1, 0, "E"),
    SOUTH: (0, 1, "S"),
    WEST: (-1, 0, "W"),
}
"""Wall bit -> (dx, dy, letter used in the solution path)."""

OPPOSITE: Dict[int, int] = {NORTH: SOUTH, SOUTH: NORTH, EAST: WEST, WEST: EAST}

ALGORITHMS: Tuple[str, ...] = ("backtracker", "prim")

# The "42" drawn with fully closed cells (X). 7 columns x 5 rows: the middle
# column is always empty, so the maze centre stays an open corridor.
PATTERN_42: Tuple[str, ...] = (
    "X.X.XXX",
    "X.X...X",
    "XXX.XXX",
    "..X.X..",
    "..X.XXX",
)
PATTERN_WIDTH: int = len(PATTERN_42[0])
PATTERN_HEIGHT: int = len(PATTERN_42)


class MazeError(Exception):
    """Raised when the maze parameters are impossible."""


class MazeGenerator:
    """Generate a random (optionally perfect) maze on a rectangular grid.

    Attributes:
        width: Number of columns.
        height: Number of rows.
        entry: Entry cell ``(x, y)``.
        exit: Exit cell ``(x, y)``.
        perfect: True for a single-path maze (a spanning tree), False for a
            Pac-Man-like board with loops and (almost) no dead-ends.
        seed: Seed used by the random generator (reproducibility).
        algorithm: ``"backtracker"`` (default) or ``"prim"``.
        grid: ``grid[y][x]`` is the wall bitmask of the cell ``(x, y)``.
        pattern_cells: Fully closed cells that draw the "42".
        pattern_skipped: True if the maze was too small for the "42".
    """

    def __init__(
        self,
        width: int,
        height: int,
        entry: Coord = (0, 0),
        exit: Optional[Coord] = None,
        perfect: bool = True,
        seed: Optional[int] = None,
        algorithm: str = "backtracker",
    ) -> None:
        """Store and validate the parameters (nothing is generated yet).

        Args:
            width: Number of columns (>= 1).
            height: Number of rows (>= 1).
            entry: Entry coordinates ``(x, y)``.
            exit: Exit coordinates ``(x, y)``; defaults to the opposite
                corner of the entry.
            perfect: Whether the maze must have exactly one path.
            seed: Random seed; a random one is drawn when None.
            algorithm: Name of the carving algorithm (see ``ALGORITHMS``).

        Raises:
            MazeError: If a parameter is invalid.
        """
        self.width: int = width
        self.height: int = height
        self.entry: Coord = entry
        self.exit: Coord = exit if exit is not None else (width - 1,
                                                          height - 1)
        self.perfect: bool = perfect
        self.seed: int = (seed if seed is not None
                          else random.randrange(2 ** 32))
        self.algorithm: str = algorithm
        self.grid: List[List[int]] = []
        self.pattern_cells: Set[Coord] = set()
        self.pattern_skipped: bool = False
        self._rng: random.Random = random.Random(self.seed)
        self._validate()

    # ------------------------------------------------------------------ #
    # Validation helpers
    # ------------------------------------------------------------------ #
    def _validate(self) -> None:
        """Check that the parameters describe a buildable maze.

        Raises:
            MazeError: On any impossible parameter.
        """
        if self.width < 1 or self.height < 1:
            raise MazeError("WIDTH and HEIGHT must be positive integers.")
        if self.width * self.height < 2:
            raise MazeError("the maze needs at least 2 cells "
                            "(entry and exit must be different).")
        if self.algorithm not in ALGORITHMS:
            raise MazeError(f"unknown algorithm '{self.algorithm}' "
                            f"(choose one of: {', '.join(ALGORITHMS)}).")
        for name, (x, y) in (("ENTRY", self.entry), ("EXIT", self.exit)):
            if not self.in_bounds(x, y):
                raise MazeError(
                    f"{name} ({x},{y}) is outside the maze "
                    f"(x must be in 0..{self.width - 1}, "
                    f"y in 0..{self.height - 1}).")
        if self.entry == self.exit:
            raise MazeError("ENTRY and EXIT must be different cells.")

    def in_bounds(self, x: int, y: int) -> bool:
        """Return True if ``(x, y)`` is inside the grid."""
        return 0 <= x < self.width and 0 <= y < self.height

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def generate(self, seed: Optional[int] = None) -> List[List[int]]:
        """Generate (or re-generate) the maze.

        Args:
            seed: Optional new seed. When None the stored seed is reused, so
                calling ``generate()`` twice gives the same maze.

        Returns:
            The wall grid, ``grid[y][x]``.
        """
        if seed is not None:
            self.seed = seed
        self._rng = random.Random(self.seed)
        self.grid = [[ALL_WALLS] * self.width for _ in range(self.height)]
        self._place_pattern()
        if self.algorithm == "prim":
            self._carve_prim()
        else:
            self._carve_backtracker()
        if not self.perfect:
            self._braid()
        return self.grid

    def solve(self) -> str:
        """Return the shortest path from entry to exit as N/E/S/W letters.

        Uses a breadth-first search, which always finds a shortest path in
        an unweighted graph.

        Returns:
            The path, e.g. ``"EESWS"``; an empty string if unreachable.
        """
        path = self.solution_cells()
        letters: List[str] = []
        for (x1, y1), (x2, y2) in zip(path, path[1:]):
            for dx, dy, letter in DIRECTIONS.values():
                if (x1 + dx, y1 + dy) == (x2, y2):
                    letters.append(letter)
        return "".join(letters)

    def solution_cells(self) -> List[Coord]:
        """Return the cells of a shortest path, entry and exit included."""
        if not self.grid:
            return []
        parent: Dict[Coord, Optional[Coord]] = {self.entry: None}
        queue: deque[Coord] = deque([self.entry])
        while queue:
            cell = queue.popleft()
            if cell == self.exit:
                break
            for nxt in self.open_neighbours(cell):
                if nxt not in parent:
                    parent[nxt] = cell
                    queue.append(nxt)
        if self.exit not in parent:
            return []
        path: List[Coord] = []
        current: Optional[Coord] = self.exit
        while current is not None:
            path.append(current)
            current = parent[current]
        path.reverse()
        return path

    def has_wall(self, x: int, y: int, wall: int) -> bool:
        """Return True if cell ``(x, y)`` has the given wall closed."""
        return bool(self.grid[y][x] & wall)

    def open_neighbours(self, cell: Coord) -> List[Coord]:
        """Return the neighbours reachable from *cell* (no wall between)."""
        x, y = cell
        result: List[Coord] = []
        for wall, (dx, dy, _) in DIRECTIONS.items():
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny) and not self.grid[y][x] & wall:
                result.append((nx, ny))
        return result

    def to_hex_lines(self) -> List[str]:
        """Return the grid as rows of hexadecimal digits (one per cell)."""
        return ["".join(f"{cell:X}" for cell in row) for row in self.grid]

    # ------------------------------------------------------------------ #
    # "42" pattern
    # ------------------------------------------------------------------ #
    def _place_pattern(self) -> None:
        """Mark the cells of the centred "42" as fully closed (blocked).

        The pattern needs a free border of one cell around it so the rest
        of the maze stays connected. If the maze is too small, or if the
        entry/exit would be covered, the pattern is skipped.
        """
        self.pattern_cells = set()
        self.pattern_skipped = False
        if (self.width < PATTERN_WIDTH + 2
                or self.height < PATTERN_HEIGHT + 2):
            self.pattern_skipped = True
            return
        # The empty middle column of the pattern sits exactly on the centre
        # cell (width // 2, height // 2), where the Pac-Man player starts.
        left = self.width // 2 - PATTERN_WIDTH // 2
        top = self.height // 2 - PATTERN_HEIGHT // 2
        cells = {
            (left + col, top + row)
            for row, line in enumerate(PATTERN_42)
            for col, char in enumerate(line)
            if char == "X"
        }
        if self.entry in cells or self.exit in cells:
            self.pattern_skipped = True
            return
        self.pattern_cells = cells

    # ------------------------------------------------------------------ #
    # Carving
    # ------------------------------------------------------------------ #
    def _carvable_neighbours(self, cell: Coord) -> List[Tuple[int, Coord]]:
        """Return ``(wall, neighbour)`` pairs that are in bounds and free."""
        x, y = cell
        result: List[Tuple[int, Coord]] = []
        for wall, (dx, dy, _) in DIRECTIONS.items():
            nxt = (x + dx, y + dy)
            if self.in_bounds(*nxt) and nxt not in self.pattern_cells:
                result.append((wall, nxt))
        return result

    def _remove_wall(self, cell: Coord, wall: int) -> None:
        """Open *wall* of *cell* and the matching wall of its neighbour.

        Updating both cells keeps the encoding coherent.
        """
        x, y = cell
        dx, dy, _ = DIRECTIONS[wall]
        self.grid[y][x] &= ~wall
        self.grid[y + dy][x + dx] &= ~OPPOSITE[wall]

    def _carve_backtracker(self) -> None:
        """Recursive backtracker (randomised depth-first search).

        Implemented iteratively with an explicit stack so large mazes never
        hit Python's recursion limit. The result is a spanning tree of the
        free cells, i.e. a perfect maze.
        """
        start = self.entry
        visited: Set[Coord] = {start}
        stack: List[Coord] = [start]
        while stack:
            cell = stack[-1]
            options = [(w, n) for w, n in self._carvable_neighbours(cell)
                       if n not in visited]
            if not options:
                stack.pop()
                continue
            wall, nxt = self._rng.choice(options)
            self._remove_wall(cell, wall)
            visited.add(nxt)
            stack.append(nxt)

    def _carve_prim(self) -> None:
        """Randomised Prim's algorithm (also yields a perfect maze)."""
        start = self.entry
        visited: Set[Coord] = {start}
        frontier: List[Tuple[Coord, int, Coord]] = [
            (start, w, n) for w, n in self._carvable_neighbours(start)
        ]
        while frontier:
            index = self._rng.randrange(len(frontier))
            frontier[index], frontier[-1] = frontier[-1], frontier[index]
            cell, wall, nxt = frontier.pop()
            if nxt in visited:
                continue
            self._remove_wall(cell, wall)
            visited.add(nxt)
            frontier.extend((nxt, w, n)
                            for w, n in self._carvable_neighbours(nxt)
                            if n not in visited)

    # ------------------------------------------------------------------ #
    # Non-perfect mode (Pac-Man board)
    # ------------------------------------------------------------------ #
    def _braid(self) -> None:
        """Remove dead-ends by opening one extra wall in each of them.

        Every opened wall creates a loop. A wall is only opened if it does
        not create a 3x3 open area. Neighbours that are also dead-ends are
        preferred, so one opening fixes two dead-ends at once.
        """
        cells = [(x, y) for y in range(self.height) for x in range(self.width)
                 if (x, y) not in self.pattern_cells]
        self._rng.shuffle(cells)
        for cell in cells:
            if len(self.open_neighbours(cell)) != 1:
                continue
            x, y = cell
            options = [(w, n) for w, n in self._carvable_neighbours(cell)
                       if self.grid[y][x] & w
                       and not self._creates_open_area(cell, w)]
            if not options:
                continue
            dead = [(w, n) for w, n in options
                    if len(self.open_neighbours(n)) == 1]
            wall, _ = self._rng.choice(dead or options)
            self._remove_wall(cell, wall)
        self._ensure_loops(2)

    def _ensure_loops(self, minimum: int) -> None:
        """Open random extra walls until the board has *minimum* loops.

        For a connected graph the number of independent loops is
        ``edges - nodes + 1``.
        """
        free = [(x, y) for y in range(self.height) for x in range(self.width)
                if (x, y) not in self.pattern_cells]
        candidates = [(c, w) for c in free
                      for w, _ in self._carvable_neighbours(c)
                      if w in (EAST, SOUTH)]
        self._rng.shuffle(candidates)
        for cell, wall in candidates:
            if self._count_loops(free) >= minimum:
                return
            x, y = cell
            closed = bool(self.grid[y][x] & wall)
            if closed and not self._creates_open_area(cell, wall):
                self._remove_wall(cell, wall)

    def _count_loops(self, free: List[Coord]) -> int:
        """Return ``edges - nodes + 1`` for the free cells."""
        edges = sum(1 for (x, y) in free for w in (EAST, SOUTH)
                    if self.in_bounds(x + DIRECTIONS[w][0],
                                      y + DIRECTIONS[w][1])
                    and not self.grid[y][x] & w)
        return edges - len(free) + 1

    def _creates_open_area(self, cell: Coord, wall: int) -> bool:
        """Return True if opening *wall* would leave a 3x3 fully open area.

        Only the 3x3 blocks containing both cells of the wall can change,
        so only those are checked (on a temporary copy of the two cells).
        """
        x, y = cell
        dx, dy, _ = DIRECTIONS[wall]
        nx, ny = x + dx, y + dy
        saved = (self.grid[y][x], self.grid[ny][nx])
        self._remove_wall(cell, wall)
        try:
            for top in range(min(y, ny) - 2, max(y, ny) + 1):
                for left in range(min(x, nx) - 2, max(x, nx) + 1):
                    if self._block_open(left, top):
                        return True
            return False
        finally:
            self.grid[y][x], self.grid[ny][nx] = saved

    def _block_open(self, left: int, top: int) -> bool:
        """Return True if the 3x3 block at ``(left, top)`` has no inner wall.
        """
        if not (self.in_bounds(left, top)
                and self.in_bounds(left + 2, top + 2)):
            return False
        for y in range(top, top + 3):
            for x in range(left, left + 3):
                if x < left + 2 and self.grid[y][x] & EAST:
                    return False
                if y < top + 2 and self.grid[y][x] & SOUTH:
                    return False
        return True
