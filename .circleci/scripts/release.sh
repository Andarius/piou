#!/usr/bin/env bash

set -xeuo pipefail

cd "$(dirname "$0")/../.." || exit

git config --global user.email "$CI_EMAIL"
git config --global user.name "$CI_USER"


uv run --only-group=bump cz bump --yes

if [ $? -eq 0 ]; then
  readonly TAG=$(poetry version -s)
  uv run --only-group=bump cz changelog "$TAG"
  uv build
  # We need to push before releasing so that the pyproject.toml matches
  # for the cache
  git push origin master
  gh release create -F CHANGELOG.md "$TAG" ./dist/*.whl
fi
