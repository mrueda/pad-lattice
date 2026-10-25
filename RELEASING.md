# Releasing Pad-Lattice

Pad-Lattice publishes with GitHub Actions and PyPI trusted publishing. No PyPI
API token is stored in GitHub.

## Release policy

Annotated Git tags are the canonical stable release records. Pad-Lattice does
not use GitHub Release objects. If a GitHub Release object is ever removed,
preserve its associated tag and do not use `--cleanup-tag`.

Pushing an annotated tag in stable `vX.Y.Z` form automatically starts
`.github/workflows/publish-pypi.yml`. The workflow rejects lightweight tags,
non-stable versions, tags that do not match the canonical Python version, and
versions without a dated `CHANGELOG.md` entry. It then tests, builds, and
validates the distributions before the `pypi` environment may obtain an OIDC
credential and publish them.

Never reuse a published version, move a published tag, or recreate a tag to
change its source revision.

## Desktop preview builds

**Build desktop installers** is manually dispatched with `main` for an
unreleased preview or an existing annotated version tag for a release build.
It builds Linux x64/ARM64 and macOS Intel/Apple Silicon packages, verifies the
bundled engine and native window, and uploads installers with SHA-256 checksums
and their source revision as workflow artifacts. It does not publish a GitHub
Release or trigger PyPI. Public installer hosting and signing/notarization must
be settled before advertising a desktop release.

All desktop metadata must match `src/pad_lattice/__init__.py`; run
`python scripts/check_desktop_versions.py` before building.

## One-time PyPI setup

Create the `pypi` environment under the repository's GitHub
**Settings > Environments** and require manual approval.

Register the production publisher at
<https://pypi.org/manage/account/publishing/>:

| Field | Value |
| --- | --- |
| PyPI project name | `pad-lattice` |
| Owner | `mrueda` |
| Repository | `pad-lattice` |
| Workflow | `publish-pypi.yml` |
| Environment | `pypi` |

## PyPI release

1. Finalize the canonical Python version and move the release notes from
   `Unreleased` into a dated `CHANGELOG.md` section.
2. Run all release tests, including the Python matrix, virtual-surface tests,
   documentation build, generated-asset checks, distribution build, and clean
   wheel installation.
3. Commit the exact release state, push `main`, and record the release commit.
4. Create and push one annotated tag that matches the Python version:

```bash
git tag -a vX.Y.Z -m "Tagging version X.Y.Z" <commit>
git push origin vX.Y.Z
```

5. Confirm that **Publish to PyPI** succeeds. The tag push is the publication
   trigger; there is no separate manual workflow run or GitHub Release step.
6. Verify the public installation in a new environment:

```bash
pipx install pad-lattice
pad-lattice --version
pad-lattice profile list
```

Pushing the stable tag is the irreversible release action. Do not push it until
the release commit and all preflight checks are final. If publication fails
before PyPI accepts the files, fix the configuration and rerun the failed
workflow job without moving or recreating the tag.

Pad-Lattice does not currently publish a Docker image. If one is added, keep
Docker publication manually dispatched from the same stable tag so both
registries use the identical source revision.
