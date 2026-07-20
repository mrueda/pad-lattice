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

## One-time setup

Create the `testpypi` and `pypi` environments under the repository's GitHub
**Settings > Environments**. Require manual approval for the `pypi`
environment.

Register a pending GitHub publisher at
<https://test.pypi.org/manage/account/publishing/> with these values:

| Field | Value |
| --- | --- |
| PyPI project name | `pad-lattice` |
| Owner | `mrueda` |
| Repository | `pad-lattice` |
| Workflow | `publish-testpypi.yml` |
| Environment | `testpypi` |

Register the production publisher at
<https://pypi.org/manage/account/publishing/>:

| Field | Value |
| --- | --- |
| PyPI project name | `pad-lattice` |
| Owner | `mrueda` |
| Repository | `pad-lattice` |
| Workflow | `publish-pypi.yml` |
| Environment | `pypi` |

## TestPyPI

Before publishing, move the relevant entries from `Unreleased` in
`CHANGELOG.md` into a new `## VERSION - YYYY-MM-DD` section and restore an
empty `Unreleased` section for subsequent work.

Run **Publish to TestPyPI** from the GitHub Actions tab. The workflow tests the
package, builds its wheel and source archive, validates the metadata, installs
the wheel in a clean environment, and publishes through the `testpypi`
environment. The workflow accepts only PEP 440 pre-release versions. The
current planned alpha is `0.1.0a1`. TestPyPI runs from `main` and does not use
or create a release tag.

Verify the uploaded package in a clean virtual environment:

```bash
python3 -m venv /tmp/pad-lattice-testpypi
/tmp/pad-lattice-testpypi/bin/python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  pad-lattice==0.1.0a1
/tmp/pad-lattice-testpypi/bin/pad-lattice --version
/tmp/pad-lattice-testpypi/bin/pad-lattice profile list
```

Index versions and distribution files are immutable. Change `__version__` to
`0.1.0a2`, `0.1.0a3`, and so on before publishing another alpha build with
different contents.

## Stable PyPI release

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
