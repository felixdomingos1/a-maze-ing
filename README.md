*This project has been created as part of the 42 curriculum by fsanjala.*

# A-Maze-ing

## Description

A-Maze-ing is a Python maze generator. It reads a `KEY=VALUE` configuration
file, generates a random but reproducible maze, writes it to a file using a
hexadecimal wall encoding, and displays it in the terminal with an interactive
menu.

Two kinds of maze can be generated:

* **Perfect** (`PERFECT=True`): exactly one path between any two cells, so
  there are no loops. Mathematically, it is a *spanning tree* of the grid.
* **Pac-Man board** (`PERFECT=False`): every corridor is reachable, the
  corners and the centre are open, there are many independent loops and
  **no dead-ends at all** (a fully "braided" board, which is the bonus).

Every maze shows a "42" drawn with fully closed cells in its centre, when the
maze is large enough (at least 9x7).

The generation logic is a reusable, pip-installable package called
`mazegen` (see [Reusable module](#reusable-module-mazegen)).

## Instructions

Requirements: Python 3.10 or later. The program itself has no third-party
dependency. The tools in `requirements.txt` are only used for linting,
testing and building.

```bash
make venv && . .venv/bin/activate   # optional: isolated environment
make install       # pip install flake8, mypy, pytest, build
make run           # python3 a_maze_ing.py config.txt
make debug         # same, under pdb
make lint          # flake8 + mypy (mandatory flags)
make lint-strict   # flake8 + mypy --strict
make test          # pytest unit tests
make build         # build mazegen-1.0.0 (.whl + .tar.gz) and copy it to the root
make clean         # remove caches and build files
```

Or directly: `python3 a_maze_ing.py config.txt`.

### Interactive menu

| Key | Action |
|-----|--------|
| 1 | Re-generate a new maze (new random seed; the output file is rewritten) |
| 2 | Show / hide the shortest path from entry to exit |
| 3 | Rotate the wall colour |
| 4 | Rotate the colour of the "42" pattern |
| 5 | Quit |

Colours: magenta = entry, red = exit, cyan = path. If standard input is not a
terminal (for example `python3 a_maze_ing.py config.txt < /dev/null`), the
maze is printed once and the program exits.

### Configuration file

One `KEY=VALUE` per line. Lines starting with `#` and blank lines are ignored.
Keys are case-insensitive. Unknown or duplicated keys are errors.

| Key | Mandatory | Description | Example |
|-----|-----------|-------------|---------|
| `WIDTH` | yes | Number of columns (1-1000) | `WIDTH=20` |
| `HEIGHT` | yes | Number of rows (1-1000) | `HEIGHT=15` |
| `ENTRY` | yes | Entry `x,y` (x = column, y = row) | `ENTRY=0,0` |
| `EXIT` | yes | Exit `x,y`, which must differ from the entry | `EXIT=19,14` |
| `OUTPUT_FILE` | yes | Output file path | `OUTPUT_FILE=maze.txt` |
| `PERFECT` | yes | `True`/`False` (also `1`/`0`, `yes`/`no`) | `PERFECT=False` |
| `SEED` | no | Integer seed. If absent, a random seed is used | `SEED=42` |
| `ALGORITHM` | no | `backtracker` (default) or `prim` | `ALGORITHM=prim` |

Every error (missing file, bad syntax, coordinates out of bounds, entry equal
to exit, unwritable output, ...) prints a clear message and exits with code 1,
without a traceback. If the maze is too small for the "42", or the entry or
exit lies on it, an error message is printed and the pattern is omitted.

### Output file

One hexadecimal digit per cell, one row per line. Bit 0 = North, 1 = East,
2 = South, 3 = West, and a set bit means the wall is closed. Then come an empty
line, the entry `x,y`, the exit `x,y`, and the shortest path written with
`N E S W`. You can check an output file with the analyzer supplied with the
subject:

```bash
python3 maze_analyzer.py maze.txt --max-dead-ends 0
```

## Maze generation algorithm

1. All cells start with their 4 walls closed. The "42" cells are marked as
   blocked and are never carved.
2. **Recursive backtracker** (randomised depth-first search, the default),
   implemented with an explicit stack: from the current cell, move to a random
   unvisited neighbour and remove the wall between them. When there is no
   unvisited neighbour left, backtrack. The result is a spanning tree, which
   means a perfect maze. **Randomised Prim** is available as an alternative.
3. If `PERFECT=False`, the maze is **braided**: each dead-end (a cell with a
   single opening) gets one extra wall opened, preferably towards another
   dead-end. Each opening creates a loop. A wall is never opened if that
   would create a 3x3 open area, so corridors stay at most 2 cells wide.
4. The shortest path is found with a **breadth-first search** (BFS).

**Why this algorithm?** The backtracker is simple to understand and to
explain. It runs in linear time and produces long, winding corridors with few
branches, which look good and are hard to solve. Because a spanning tree has
no 2x2 open block, the "corridors at most 2 wide" rule holds automatically in
perfect mode. Braiding a perfect maze is the simplest way to get a connected
board with loops and no dead-ends.

## Reusable module (`mazegen`)

The `mazegen/` package contains a single class, `MazeGenerator`. It has no
dependencies and does not know about config files or the terminal. Build it
with `make build`, which produces `mazegen-1.0.0-py3-none-any.whl` and
`mazegen-1.0.0.tar.gz` at the repository root. Install it with
`pip install mazegen-1.0.0-py3-none-any.whl`.

```python
from mazegen import MazeGenerator, EAST

gen = MazeGenerator(width=30, height=20, entry=(0, 0), exit=(29, 19),
                    perfect=False, seed=1234, algorithm="backtracker")
gen.generate()                 # same seed -> same maze
gen.generate(seed=99)          # re-generate with another seed

gen.grid[y][x]                 # wall bitmask of cell (x, y): N=1 E=2 S=4 W=8
gen.has_wall(3, 2, EAST)       # is the east wall of (3, 2) closed?
gen.open_neighbours((3, 2))    # cells reachable in one step
gen.solve()                    # shortest path, e.g. "EESSWN..."
gen.solution_cells()           # same path as a list of (x, y)
gen.pattern_cells              # cells of the "42"
```

Invalid parameters raise `mazegen.MazeError`. The full package documentation
is in `MAZEGEN.md`, which is shipped with the package. The rest of the
project (`amazeing/` for config, output and display, and `a_maze_ing.py`) is
specific to this program.

## Project structure

```
a_maze_ing.py        main program (menu, error handling)
config.txt           default configuration
amazeing/config.py   config parsing and validation
amazeing/output.py   hexadecimal output file
amazeing/display.py  terminal renderer (ANSI colours)
mazegen/generator.py reusable MazeGenerator class
tests/               pytest unit tests (not graded)
pyproject.toml       package build configuration
```

## Team and project management

* **Roles:** `fsanjala`: design, implementation, tests and documentation.
* **Planning:** (1) read the subject and the analyzer; (2) reusable generator
  for perfect mazes plus the output format, validated with
  `maze_analyzer.py`; (3) "42" pattern; (4) Pac-Man mode (braiding);
  (5) terminal display and menu; (6) packaging, lint, README. The "42"
  placement was changed during the project: its empty middle column now
  always covers the centre cell, so the player start stays open for even
  sizes too.
* **What worked well:** checking every change with the provided analyzer over
  hundreds of seeds, sizes and algorithms. Keeping the generator separate
  from I/O.
* **What could be improved:** a MiniLibX graphical display and an animated
  generation.
* **Tools:** Python venv, flake8, mypy, pytest, `python -m build`,
  `maze_analyzer.py`.

## Advanced features (bonus)

* Pac-Man mode with **zero dead-ends** (`maze_analyzer.py --max-dead-ends 0`
  reports "bonus-grade").
* **Two generation algorithms:** recursive backtracker and Prim
  (`ALGORITHM=` key).

## Resources

* Jamis Buck, *Mazes for Programmers* (Pragmatic Bookshelf, 2015).
* Jamis Buck's blog, "Maze Generation" series:
  <https://weblog.jamisbuck.org/2011/2/7/maze-generation-algorithm-recap>
* Wikipedia: *Maze generation algorithm*, *Spanning tree*,
  *Breadth-first search*.
* Think Labyrinth, "Maze terminology" (braid mazes):
  <https://www.astrolog.org/labyrnth/algrithm.htm>
* Python docs: `random`, `collections.deque`, `dataclasses`, `typing`;
  PEP 8, PEP 257, PEP 484; the Python Packaging User Guide (`pyproject.toml`).
* Choose a License: <https://choosealicense.com/licenses/mit/>

**AI usage:** an AI assistant (Claude) was used to write a first version of
the code, the tests and this documentation. All of it was then reviewed and
tested with `maze_analyzer.py`, and every part can be explained.
*(Adapt this paragraph to how you really worked.)*
