# Releasing Pad-Lattice

## Prepare

1. Finalize the canonical Python version and move the release notes from
   `Unreleased` into a dated `CHANGELOG.md` section.
2. Run `python scripts/check_desktop_versions.py` and confirm build/test,
   desktop installer checks, and documentation builds pass.
3. Commit the exact release state, push `main`, and record the release commit.
4. Create and push one annotated tag that matches the Python version:

```bash
git tag -a vX.Y.Z -m "Tagging version X.Y.Z" <commit>
git push origin vX.Y.Z
```

Pushing a tag does **not** publish to PyPI.

## Desktop Installers

1. Run **Build desktop installers** with `ref=vX.Y.Z` and `platform=all`.
2. Confirm all four platform jobs and the Stream Deck job pass. Download their artifacts and verify
   the source revision and SHA-256 checksums.
3. Create a GitHub release draft for that tag. Attach the Linux AppImages,
   macOS DMGs, Stream Deck plugin, and checksum files, with concise release notes.
4. Review the downloads and installation instructions before publishing the draft.

Use `ref=main` only for development builds, not tagged release assets.

## PyPI

Open **Actions > Publish to PyPI > Run workflow**, select `main`, and enter
`X.Y.Z` in **version** (without `v`). Alternatively:

```bash
gh workflow run publish-pypi.yml --ref main -f version=X.Y.Z
```

The workflow checks out the matching tag, validates the version and changelog,
and tests the distributions before publishing. Approve the `pypi` environment
if required, then verify installation in a clean environment:

```bash
pipx install pad-lattice==X.Y.Z
pad-lattice --version
pad-lattice profile list
```

Never reuse a published version or move a release tag. Retry failed jobs without
retagging. Deleting a GitHub Release must preserve its tag; do not use `--cleanup-tag`.

<details>
<summary>One-time PyPI Trusted Publishing setup</summary>

Register `mrueda/pad-lattice` as the publisher for the `pad-lattice` PyPI project,
using workflow `publish-pypi.yml` and GitHub environment `pypi`. Configure required
reviewers on that environment for an additional approval step. No PyPI API token
is needed in GitHub.

</details>
