#!/usr/bin/env python3
"""A-Maze-ing: generate a maze from a config file, save it and display it.

Usage:
    python3 a_maze_ing.py config.txt
"""

from __future__ import annotations

import random
import sys
from typing import List

from amazeing.config import Config, ConfigError, load_config
from amazeing.display import Renderer
from amazeing.output import OutputError, write_maze
from mazegen import MazeError, MazeGenerator

MENU: str = (
    "\n=== A-Maze-ing ===\n"
    "1. Re-generate a new maze\n"
    "2. Show/Hide path from entry to exit\n"
    "3. Rotate maze wall colours\n"
    "4. Rotate '42' colours\n"
    "5. Quit"
)
CLEAR_SCREEN: str = "\033[H\033[2J"


def build_maze(config: Config) -> MazeGenerator:
    """Create and generate the maze described by *config*.

    Raises:
        MazeError: If the parameters are impossible.
    """
    maze = MazeGenerator(
        width=config.width,
        height=config.height,
        entry=config.entry,
        exit=config.exit,
        perfect=config.perfect,
        seed=config.seed,
        algorithm=config.algorithm,
    )
    maze.generate()
    return maze


def warn_pattern(maze: MazeGenerator) -> None:
    """Print an error message if the "42" could not be drawn."""
    if maze.pattern_skipped:
        print("Error: the maze is too small (or the entry/exit is in the "
              "way) to draw the '42' pattern; it was omitted.",
              file=sys.stderr)


def show(maze: MazeGenerator, renderer: Renderer, message: str) -> None:
    """Clear the terminal and print the maze, a status line and the menu."""
    print(CLEAR_SCREEN, end="")
    print(renderer.render(maze))
    print(f"\nSeed: {maze.seed}  |  Algorithm: {maze.algorithm}  |  "
          f"Perfect: {maze.perfect}  |  Path length: {len(maze.solve())}")
    warn_pattern(maze)
    if message:
        print(message)
    print(MENU)


def interactive_loop(maze: MazeGenerator, config: Config) -> None:
    """Run the user menu until the user quits (or stdin is closed)."""
    renderer = Renderer()
    message = f"Maze written to '{config.output_file}'."
    while True:
        show(maze, renderer, message)
        try:
            choice = input("Choice? (1-5): ").strip()
        except EOFError:
            print()
            return
        message = ""
        if choice == "1":
            maze.generate(seed=random.randrange(2 ** 32))
            write_maze(maze, config.output_file)
            message = f"New maze written to '{config.output_file}'."
        elif choice == "2":
            renderer.show_path = not renderer.show_path
        elif choice == "3":
            message = f"Wall colour: {renderer.next_wall_colour()}"
        elif choice == "4":
            message = f"'42' colour: {renderer.next_pattern_colour()}"
        elif choice == "5":
            return
        else:
            message = f"Invalid choice '{choice}'. Type a number from 1 to 5."


def main(argv: List[str]) -> int:
    """Program entry point; returns the process exit code."""
    if len(argv) != 1:
        print("Usage: python3 a_maze_ing.py <config_file>", file=sys.stderr)
        return 1
    try:
        config = load_config(argv[0])
        maze = build_maze(config)
        write_maze(maze, config.output_file)
        if not sys.stdin.isatty():
            warn_pattern(maze)
            print(Renderer().render(maze))
            return 0
        interactive_loop(maze, config)
    except (ConfigError, MazeError) as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return 1
    except OutputError as error:
        print(f"Output error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        print("\nInterrupted. Bye!")
        sys.exit(130)
    except Exception as error:  # last safety net: never show a traceback
        print(f"Unexpected error: {error}", file=sys.stderr)
        sys.exit(1)
