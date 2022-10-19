#!/usr/bin/env bash

set -xe

cd "$(dirname "$0")/../.." || exit

git config --global user.email "$CI_EMAIL"
git config --global user.name "$CI_USER"

poetry run cz bump --changelog --yes

if [ $? -eq 0 ]; then
  git push origin master
  readonly TAG=$(poetry version -s)
  poetry build
  gh release create -F CHANGELOG.md "$TAG" ./dist/*.whl
fi
