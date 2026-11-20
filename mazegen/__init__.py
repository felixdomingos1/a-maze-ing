"""mazegen - a reusable maze generator.

Example:
    >>> from mazegen import MazeGenerator
    >>> gen = MazeGenerator(width=10, height=8, seed=1)
    >>> grid = gen.generate()
    >>> path = gen.solve()
"""

from mazegen.generator import (
    ALGORITHMS,
    ALL_WALLS,
    EAST,
    NORTH,
    SOUTH,
    WEST,
    Coord,
    MazeError,
    MazeGenerator,
)

__all__ = [
    "ALGORITHMS",
    "ALL_WALLS",
    "EAST",
    "NORTH",
    "SOUTH",
    "WEST",
    "Coord",
    "MazeError",
    "MazeGenerator",
]
__version__ = "1.0.0"
