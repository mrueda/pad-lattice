# Releasing Pad-Lattice

Pad-Lattice publishes with GitHub Actions and PyPI trusted publishing. No PyPI
API token is stored in GitHub.

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
current planned alpha is `0.1.0a1`.

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

## PyPI

After alpha verification, change `__version__` to `0.1.0`, commit that release,
then create and push a matching tag:

```bash
git tag -a v0.1.0 -m "Pad-Lattice 0.1.0"
git push origin v0.1.0
```

Run **Publish to PyPI** from the GitHub Actions tab and enter `v0.1.0` as the
release tag. The workflow checks out that tag and refuses to publish when the
tag and package versions differ.

Verify the public installation:

```bash
pipx install pad-lattice
pad-lattice --version
pad-lattice profile list
```
