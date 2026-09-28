#!/usr/bin/env bash
# Cuts a release in two steps, with the release PR merged in between.
#
#   scripts/release.sh prepare patch|minor|major
#       Bumps the version on chore/release-X.Y.Z from develop and opens a PR to develop.
#   scripts/release.sh publish [SUMMARY_FILE]
#       On develop with the PR merged: fast-forwards main, pushes the annotated vX.Y.Z tag
#       (message: the summary) and waits for release.yml to create the GitHub Release.
#
# YES=1 skips the confirmation prompt.
set -euo pipefail

REPO=$(git remote get-url origin | sed -E 's#^.*github\.com[:/]##; s#\.git$##')

die() {
    echo "release: $*" >&2
    exit 1
}

last_tag() {
    git describe --tags --match 'v[0-9]*' --abbrev=0 HEAD
}

tag_exists() {
    git rev-parse -q --verify "refs/tags/$1" >/dev/null ||
        [ -n "$(git ls-remote --tags origin "refs/tags/$1")" ]
}

# On develop, clean (untracked files aside) and level with origin/develop.
require_develop() {
    [ -z "$(git status --porcelain --untracked-files=no)" ] || die "the working tree has changes"
    git switch -q develop
    git pull -q --ff-only origin develop
    [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/develop)" ] || die "develop differs from origin/develop"
}

# Waits for the workflow run on a commit (or tag) and fails unless it succeeds.
wait_for_run() {
    local workflow=$1 filter=$2 value=$3 id=""
    for _ in $(seq 30); do
        id=$(gh run list --repo "$REPO" --workflow "$workflow" "$filter" "$value" \
            --json databaseId -q '.[0].databaseId')
        [ -n "$id" ] && break
        sleep 5
    done
    [ -n "$id" ] || die "no $workflow run for $value"
    echo "Waiting for $workflow on $value (run $id)..."
    gh run watch "$id" --repo "$REPO" --exit-status --interval 15 >/dev/null ||
        die "$workflow failed: gh run view $id --repo $REPO"
}

confirm() {
    [ "${YES:-0}" = 1 ] && return
    local answer
    read -r -p "$1 [y/N] " answer
    [ "$answer" = y ] || die "stopped"
}

prepare() {
    local bump=${1:-}
    case $bump in patch | minor | major) ;; *) die "usage: release.sh prepare patch|minor|major" ;; esac

    require_develop
    local version branch
    version=$(uv version --bump "$bump" --dry-run --short)
    branch="chore/release-$version"
    ! tag_exists "v$version" || die "v$version already exists"
    [ -n "$(git log --oneline "$(last_tag)..HEAD")" ] || die "nothing since $(last_tag)"
    wait_for_run tests.yml --commit "$(git rev-parse HEAD)"

    git switch -q -c "$branch"
    uv version --bump "$bump" >/dev/null
    git commit -q -m "chore(release): $version" -- pyproject.toml uv.lock
    git push -q -u origin "$branch"
    gh pr create --repo "$REPO" --base develop --head "$branch" \
        --title "chore(release): $version" --body "Bumps the version to $version."

    echo
    git cliff --unreleased --tag "v$version" --strip header 2>/dev/null
    echo
    echo "Next: merge the PR as a merge commit, write the summary, then:"
    echo "  make release-publish SUMMARY=path/to/summary.md"
}

publish() {
    local summary=${1:-}
    require_develop

    local version tag previous
    version=$(uv version --short)
    tag="v$version"
    previous=$(last_tag)
    ! tag_exists "$tag" || die "$tag already exists"
    [ "${previous#v}" != "$version" ] || die "pyproject.toml is still at $version: merge the release PR first"
    git merge-base --is-ancestor origin/main HEAD || die "main isn't an ancestor of develop, so it can't fast-forward"
    wait_for_run tests.yml --commit "$(git rev-parse HEAD)"
    make mcp-smoke

    if [ -z "$summary" ]; then
        summary=$(mktemp)
        "${EDITOR:-vi}" "$summary"
    fi
    [ -s "$summary" ] || die "the summary is empty"

    echo
    git cliff --unreleased --tag "$tag" --with-tag-message "$(cat "$summary")" --strip header 2>/dev/null
    echo
    confirm "Fast-forward main to $(git rev-parse --short HEAD) and push $tag?"

    git push origin HEAD:main
    git tag -a "$tag" --cleanup=verbatim -F "$summary"
    git push origin "$tag"
    wait_for_run release.yml --commit "$(git rev-parse HEAD)"
    gh release view "$tag" --repo "$REPO" --json url -q .url
}

case ${1:-} in
prepare) prepare "${2:-}" ;;
publish) publish "${2:-}" ;;
*) die "usage: release.sh prepare patch|minor|major | publish [SUMMARY_FILE]" ;;
esac
