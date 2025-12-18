#!/bin/bash

set -euo pipefail

cd "$(dirname "$0")/.." || exit 1


uv run coverage run -a -m examples.simple -h
uv run coverage run -a -m examples.simple foo 1 --baz 2
uv run coverage run -a -m examples.simple_main 1 --baz 2
uv run coverage run -a -m examples -h
uv run coverage run -a -m examples foo 1 --foo2 foo --foo12 '{"foo": 1, "bar": "baz"}' --foo-bar 1
uv run coverage run -a -m examples sub -h
uv run coverage run -a -m examples foo -h
uv run coverage run -a -m examples error || true
uv run coverage run -a -m examples sub foo 1 --foo2 foo
uv run coverage run -a -m examples.derived -h
uv run coverage run -a -m examples.derived bar
uv run coverage run -a -m examples.derived foo --host postgres
uv run coverage run -a -m examples.derived dynamic --db1 test
uv run coverage run -a -m examples.annotated -h
uv run coverage run -a -m examples.annotated foo 42 -b hello --foo bar
uv run coverage run -a -m examples.annotated derived -a 3 -b 2 --mode release