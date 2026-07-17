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

Run **Publish to TestPyPI** from the GitHub Actions tab. The workflow tests the
package, builds its wheel and source archive, validates the metadata, installs
the wheel in a clean environment, and publishes through the `testpypi`
environment.

Verify the uploaded package in a clean virtual environment:

```bash
python3 -m venv /tmp/pad-lattice-testpypi
/tmp/pad-lattice-testpypi/bin/python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  pad-lattice==0.1.0
/tmp/pad-lattice-testpypi/bin/pad-lattice --version
```

PyPI versions and distribution files are immutable. Change `__version__` before
publishing another build with different contents.

## PyPI

After TestPyPI verification, create and push a tag matching `__version__`:

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
```
