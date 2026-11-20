"""Unit tests for the maze generator and the config parser (pytest)."""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import List, Set

import pytest

from amazeing.config import ConfigError, load_config
from amazeing.output import format_maze
from mazegen import ALL_WALLS, EAST, SOUTH, Coord, MazeError, MazeGenerator

SIZES = [(2, 1), (3, 3), (8, 6), (9, 7), (10, 10), (20, 15), (31, 17)]
SEEDS = range(15)


def free_cells(maze: MazeGenerator) -> List[Coord]:
    """All cells that are not part of the "42"."""
    return [(x, y) for y in range(maze.height) for x in range(maze.width)
            if (x, y) not in maze.pattern_cells]


def reachable(maze: MazeGenerator) -> Set[Coord]:
    """Cells reachable from the entry (depth-first flood fill)."""
    seen = {maze.entry}
    stack = [maze.entry]
    while stack:
        for nxt in maze.open_neighbours(stack.pop()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def loops(maze: MazeGenerator) -> int:
    """Number of independent cycles: edges - nodes + 1."""
    cells = free_cells(maze)
    edges = sum(len(maze.open_neighbours(c)) for c in cells) // 2
    return edges - len(cells) + 1


def check_common(maze: MazeGenerator) -> None:
    """Properties every generated maze must have."""
    w, h = maze.width, maze.height
    for y, x in itertools.product(range(h), range(w)):
        cell = maze.grid[y][x]
        if x + 1 < w:
            assert bool(cell & EAST) == bool(maze.grid[y][x + 1] & 8)
        if y + 1 < h:
            assert bool(cell & SOUTH) == bool(maze.grid[y + 1][x] & 1)
        if y == 0:
            assert cell & 1
        if y == h - 1:
            assert cell & 4
        if x == 0:
            assert cell & 8
        if x == w - 1:
            assert cell & 2
    for px, py in maze.pattern_cells:
        assert maze.grid[py][px] == ALL_WALLS
    assert reachable(maze) == set(free_cells(maze))
    for top in range(h - 2):
        for left in range(w - 2):
            assert not maze._block_open(left, top), "3x3 open area"


@pytest.mark.parametrize("algorithm", ["backtracker", "prim"])
@pytest.mark.parametrize("size", SIZES)
def test_perfect(size: tuple[int, int], algorithm: str) -> None:
    """Perfect mode: a spanning tree (no loop at all)."""
    for seed in SEEDS:
        maze = MazeGenerator(size[0], size[1], (0, 0),
                             (size[0] - 1, size[1] - 1), True, seed,
                             algorithm)
        maze.generate()
        check_common(maze)
        assert loops(maze) == 0
        assert maze.solve()


@pytest.mark.parametrize("algorithm", ["backtracker", "prim"])
@pytest.mark.parametrize("size", [(9, 7), (10, 10), (20, 15), (31, 17)])
def test_pacman(size: tuple[int, int], algorithm: str) -> None:
    """Default mode: loops, few dead-ends, corners/centre open."""
    for seed in SEEDS:
        maze = MazeGenerator(size[0], size[1], (0, 0),
                             (size[0] - 1, size[1] - 1), False, seed,
                             algorithm)
        maze.generate()
        check_common(maze)
        assert loops(maze) >= 2
        dead = [c for c in free_cells(maze)
                if len(maze.open_neighbours(c)) == 1]
        assert len(dead) <= 4      # only the cells enclosed by the "42"
        centre = (size[0] // 2, size[1] // 2)
        assert centre not in maze.pattern_cells


def test_seed_is_reproducible() -> None:
    """The same seed gives the same maze."""
    first = MazeGenerator(15, 10, seed=7)
    second = MazeGenerator(15, 10, seed=7)
    assert first.generate() == second.generate()


def test_pattern_skipped_when_small() -> None:
    """A maze smaller than 9x7 has no "42"."""
    maze = MazeGenerator(8, 6, seed=1)
    maze.generate()
    assert maze.pattern_skipped and not maze.pattern_cells


def test_shortest_path_is_shortest() -> None:
    """On a fully open braided board the path is a Manhattan distance."""
    maze = MazeGenerator(5, 5, (0, 0), (4, 4), True, seed=3)
    maze.generate()
    path = maze.solve()
    assert path.count("E") - path.count("W") == 4
    assert path.count("S") - path.count("N") == 4


@pytest.mark.parametrize("kwargs", [
    {"width": 0, "height": 5},
    {"width": 1, "height": 1},
    {"width": 5, "height": 5, "entry": (5, 0)},
    {"width": 5, "height": 5, "entry": (1, 1), "exit": (1, 1)},
    {"width": 5, "height": 5, "algorithm": "nope"},
])
def test_invalid_parameters(kwargs: dict[str, object]) -> None:
    """Impossible parameters raise MazeError."""
    with pytest.raises(MazeError):
        MazeGenerator(**kwargs)  # type: ignore[arg-type]


def test_output_format() -> None:
    """Output file: hex rows, blank line, entry, exit, path, final \\n."""
    maze = MazeGenerator(4, 3, (0, 0), (3, 2), True, seed=2)
    maze.generate()
    lines = format_maze(maze).split("\n")
    assert all(len(row) == 4 for row in lines[:3])
    assert lines[3] == "" and lines[4] == "0,0" and lines[5] == "3,2"
    assert lines[-1] == ""


@pytest.mark.parametrize("content", [
    "WIDTH=10\n",
    "WIDTH=abc\nHEIGHT=5\nENTRY=0,0\nEXIT=1,1\nOUTPUT_FILE=a\nPERFECT=True\n",
    "WIDTH=10\nHEIGHT=5\nENTRY=0\nEXIT=1,1\nOUTPUT_FILE=a\nPERFECT=True\n",
    "WIDTH=10\nHEIGHT=5\nENTRY=0,0\nEXIT=1,1\nOUTPUT_FILE=a\nPERFECT=maybe\n",
    "WIDTH=10\nWIDTH=10\n",
    "garbage line\n",
    "WIDTH=10\nHEIGHT=5\nENTRY=0,0\nEXIT=1,1\nOUTPUT_FILE=a\nPERFECT=True\n"
    "COLOR=red\n",
])
def test_bad_configs(tmp_path: Path, content: str) -> None:
    """Every malformed config raises ConfigError (never a crash)."""
    path = tmp_path / "config.txt"
    path.write_text(content)
    with pytest.raises(ConfigError):
        load_config(str(path))


def test_missing_config() -> None:
    """A missing file raises ConfigError."""
    with pytest.raises(ConfigError):
        load_config("/nonexistent/config.txt")


def test_good_config(tmp_path: Path) -> None:
    """Comments and blank lines are ignored."""
    path = tmp_path / "config.txt"
    path.write_text("# comment\n\nWIDTH=10\nHEIGHT=5\nENTRY=0,0\n"
                    "EXIT=9,4\nOUTPUT_FILE=out.txt\nPERFECT=False\nSEED=3\n")
    config = load_config(str(path))
    assert (config.width, config.height, config.seed) == (10, 5, 3)
    assert config.exit == (9, 4) and not config.perfect
