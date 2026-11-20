all: run

PYTHON = python3
VENV = .venv
CONFIG = config.txt

install:
	$(PYTHON) -m pip install -r requirements.txt

venv:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install -r requirements.txt

run:
	$(PYTHON) a_maze_ing.py $(CONFIG)

debug:
	$(PYTHON) -m pdb a_maze_ing.py $(CONFIG)

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict

test:
	$(PYTHON) -m pytest -q tests

build:
	$(PYTHON) -m build
	cp dist/mazegen-*.whl dist/mazegen-*.tar.gz .

clean:
	rm -rf __pycache__ */__pycache__ .mypy_cache .pytest_cache build dist *.egg-info

fclean: clean
	rm -f maze.txt

.PHONY: all install venv run debug lint lint-strict test build clean fclean
