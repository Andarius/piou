#!/usr/bin/env bash
# DESCRIPTION
#   Open a `release/<version>` PR: bump the version and CHANGELOG with commitizen, use the release notes as the PR
#   body. Merging the PR tags, builds, creates the GitHub release and publishes to PyPI (.github/workflows/release.yml).
#   Notes come from .scratch/release-<version>.md if it exists, otherwise from the new CHANGELOG section.
# USAGE
#   ./bin/release.sh [-n|--dry-run] [<version>]
# EXAMPLES
#   ./bin/release.sh --dry-run        # preview the version commitizen picks, change nothing
#   ./bin/release.sh 0.39.0           # release an explicit version

set -euo pipefail

DRY_RUN=false
VERSION=""
while [[ $# -gt 0 ]]; do
    case $1 in
        -n | --dry-run) DRY_RUN=true; shift ;;
        -h | --help) sed -n '2,10p' "$0"; exit 0 ;;
        -*) echo "Unknown option: $1" >&2; exit 1 ;;
        *) VERSION="$1"; shift ;;
    esac
done

cd "$(dirname "${BASH_SOURCE[0]}")/.."
cz() { uv run -q --frozen --only-group=bump cz "$@"; }

# Preflight
[[ -z "$(git status --porcelain)" ]] || { echo "error: working tree not clean" >&2; exit 1; }
[[ "$(git branch --show-current)" == "master" ]] || { echo "error: not on master" >&2; exit 1; }
git fetch -q origin master --tags
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/master)" ]] || { echo "error: master not in sync with origin" >&2; exit 1; }

if [[ -z "$VERSION" ]]; then
    VERSION=$(cz bump --get-next 2>/dev/null) || { echo "error: no releasable commits, pass a version" >&2; exit 1; }
fi
BRANCH="release/$VERSION"
NOTES=".scratch/release-$VERSION.md"
git rev-parse -q --verify "refs/tags/$VERSION" >/dev/null && { echo "error: tag $VERSION exists" >&2; exit 1; }
git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null && { echo "error: $BRANCH exists on origin" >&2; exit 1; }

echo "Releasing $(cz version --project) → $VERSION"
if $DRY_RUN; then
    cz bump --dry-run --yes "$VERSION"
    exit 0
fi

git switch -q -c "$BRANCH"
cz bump --yes --files-only "$VERSION"
grep -qx "version = \"$VERSION\"" pyproject.toml && grep -q "^## $VERSION " CHANGELOG.md \
    || { echo "error: commitizen did not bump to $VERSION (no new commits?)" >&2; exit 1; }
uv lock -q

# Curated notes replace the generated CHANGELOG section body, keeping its header
mkdir -p .scratch
[[ -f "$NOTES" ]] || awk '/^## /{if (p) exit; p = 1; next} p' CHANGELOG.md | sed '/./,$!d' >"$NOTES"
python3 - "$NOTES" <<'EOF'
import re, sys
from pathlib import Path

notes = Path(sys.argv[1]).read_text().strip()
changelog = Path("CHANGELOG.md")
text = changelog.read_text()
first = re.search(r"^## .*$", text, re.M)
nxt = re.search(r"^## ", text[first.end():], re.M)
end = first.end() + nxt.start() if nxt else len(text)
changelog.write_text(f"{text[: first.end()]}\n\n{notes}\n\n{text[end:].lstrip()}")
EOF

git add pyproject.toml CHANGELOG.md uv.lock
git commit -q -m "chore(release): release $VERSION"
git push -q -u origin "$BRANCH"
gh pr create --base master --head "$BRANCH" --title "release $VERSION" --body-file "$NOTES"
