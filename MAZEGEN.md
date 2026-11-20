# mazegen

A small, dependency-free Python (>= 3.10) maze generator.

## Install

```bash
pip install mazegen-1.0.0-py3-none-any.whl
```

## Basic example

```python
from mazegen import MazeGenerator

gen = MazeGenerator(width=20, height=15)   # entry (0,0), exit (19,14)
gen.generate()
print(gen.solve())                          # e.g. "SSEESWS..."
```

## Custom parameters

```python
gen = MazeGenerator(
    width=30, height=20,
    entry=(0, 0), exit=(29, 19),   # (x, y) = (column, row)
    perfect=False,                 # False: Pac-Man board with loops
    seed=1234,                     # same seed -> same maze
    algorithm="prim",              # "backtracker" (default) or "prim"
)
gen.generate()
gen.generate(seed=99)              # re-generate with another seed
```

Invalid parameters raise `mazegen.MazeError`.

## Accessing the structure and a solution

* `gen.grid[y][x]` - wall bitmask of cell `(x, y)`; a set bit is a closed wall:
  `NORTH=1`, `EAST=2`, `SOUTH=4`, `WEST=8` (constants exported by `mazegen`).
* `gen.has_wall(x, y, mazegen.EAST)` - test one wall.
* `gen.open_neighbours((x, y))` - cells reachable in one step.
* `gen.pattern_cells` - fully closed cells drawing the "42"
  (`gen.pattern_skipped` is True when the maze was too small for it).
* `gen.solve()` - shortest path as a string of `N`, `E`, `S`, `W`.
* `gen.solution_cells()` - the same path as a list of `(x, y)` cells.
* `gen.to_hex_lines()` - the grid as rows of hexadecimal digits.
