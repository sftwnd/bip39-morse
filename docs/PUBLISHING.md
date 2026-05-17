# Publishing to PyPI

Step-by-step for the maintainer (sftwnd). Covers both TestPyPI (rehearsal) and production PyPI. Authentication is **OIDC trusted publishing** — no long-lived API token lives in this repository's secrets.

## Architecture

Two workflows, both with the same OIDC-based design:

| File | Trigger | Target | Sigstore attestations |
|---|---|---|---|
| `.github/workflows/release-testpypi.yml` | `workflow_dispatch` (manual) | https://test.pypi.org | off (TestPyPI's PEP 740 support is unreliable) |
| `.github/workflows/release-pypi.yml` | `release: published` (GitHub Releases UI) | https://pypi.org | on |

Each workflow has two jobs:
1. **`build`** — checks out source, runs `python -m build`, uploads `dist/` as an artefact.
2. **`publish`** — downloads the artefact (no source checkout), uploads to PyPI via `pypa/gh-action-pypi-publish` using OIDC.

Splitting build from publish reduces what a hypothetical malicious build dependency could do during the upload step.

## One-time setup

This needs to be done **before** the first publish. Order matters.

### 1. PyPI account hygiene (already done by you)

- Account on https://pypi.org (production)
- Account on https://test.pypi.org (rehearsal — separate account database)
- **2FA enabled** on both (PyPI requires it for all publishers since 2024)

### 2. GitHub repository environments

Two environments are referenced in the workflows: `testpypi` and `pypi`. They must exist as repository environments **before** the workflows can run.

These have already been created via API at repo-setup time:

```bash
gh api -X PUT repos/sftwnd/bip39-morse/environments/testpypi
gh api -X PUT repos/sftwnd/bip39-morse/environments/pypi
```

(Optional, for production only: add a required reviewer in Settings → Environments → pypi → Deployment protection rules. That gates every prod publish behind a manual approval click.)

### 3. Pending Publishers on PyPI

A "pending publisher" tells PyPI: *"this GitHub workflow is authorised to publish under this project name, even though no version exists yet."* Once the first publish happens, the project is registered and the pending publisher becomes a normal trusted publisher.

#### On TestPyPI (https://test.pypi.org)

1. Log in, go to **Account settings → Publishing → Add a new pending publisher**.
2. Fill in:
   - **PyPI project name**: `bip39-morse`
   - **Owner**: `sftwnd`
   - **Repository name**: `bip39-morse`
   - **Workflow name**: `release-testpypi.yml`
   - **Environment name**: `testpypi`
3. Add.

#### On production PyPI (https://pypi.org)

1. Log in, **Account settings → Publishing → Add a new pending publisher**.
2. Fill in:
   - **PyPI project name**: `bip39-morse`
   - **Owner**: `sftwnd`
   - **Repository name**: `bip39-morse`
   - **Workflow name**: `release-pypi.yml`
   - **Environment name**: `pypi`
3. Add.

## Publishing flows

### TestPyPI (every time you want to dry-run before a real release)

1. **Actions tab → "Publish to TestPyPI" → Run workflow → branch `master` → Run**.
2. Wait for both jobs (`build`, `publish`) to go green.
3. Verify on https://test.pypi.org/project/bip39-morse/ — the new version should appear.
4. Test the install in a clean venv:
   ```bash
   python -m venv /tmp/testvenv && source /tmp/testvenv/bin/activate
   pip install \
     --index-url https://test.pypi.org/simple/ \
     --extra-index-url https://pypi.org/simple/ \
     bip39-morse==X.Y.Z
   bip39-morse --help
   ```
   The `--extra-index-url` is needed because dependencies like `prompt_toolkit` live on production PyPI, not TestPyPI.

If something looks wrong on TestPyPI (broken README, missing classifier, etc.), fix it in a PR, merge to master, and re-run the workflow. TestPyPI does **not** allow overwriting an existing version — bump the version (e.g. `1.0.1` → `1.0.2.dev1`) or yank and republish under a new dev-suffixed version.

### Production PyPI

1. Make sure master is at the commit you want to publish, and `pyproject.toml` has the exact version you want on PyPI.
2. Cut a GitHub release: **Releases → Draft a new release → Choose tag** (use existing tag like `v1.0.2` or create a new one) **→ Publish release**.
3. The `release-pypi.yml` workflow fires automatically on the `release: published` event.
4. Wait for both jobs green; verify on https://pypi.org/project/bip39-morse/.
5. Test install:
   ```bash
   python -m venv /tmp/prodvenv && source /tmp/prodvenv/bin/activate
   pip install bip39-morse==X.Y.Z
   bip39-morse --help
   ```

## What if OIDC fails / token-fallback?

If OIDC ever breaks (PyPI side outage, GitHub Actions change, etc.) and you need to publish urgently:

1. Generate a short-lived API token on PyPI scoped to the `bip39-morse` project only (NOT account-wide).
2. Add it as a repo secret `PYPI_API_TOKEN` (or `TEST_PYPI_API_TOKEN`).
3. Add to the publish step:
   ```yaml
   - uses: pypa/gh-action-pypi-publish@release/v1
     with:
       password: ${{ secrets.PYPI_API_TOKEN }}
       # ... other params unchanged
   ```
4. **Revoke the token immediately after the publish completes.** Don't leave a long-lived token in secrets.

## Yanking a release

If a bad version ships (compromise, broken wheel, accidentally-included secret):

1. **Yank** it on PyPI: project page → release → "Options" → "Yank". This prevents new installs without breaking existing pinned ones.
2. If actually malicious or contains secrets, contact PyPI support to fully **delete**.
3. Publish the fix as a new version with a higher number (PyPI never lets you reuse a version number, even after delete).
4. Document the yank in `CHANGELOG.md` under a `### Yanked` heading and in the GitHub release notes.

## Signing & verification

The production workflow signs every artefact with sigstore via PEP 740 attestations (default in modern `pypa/gh-action-pypi-publish`). Users can verify a wheel was built by this exact workflow at a known commit:

```bash
pip install sigstore
sigstore verify identity --bundle bip39-morse-1.0.2-py3-none-any.whl.sigstore \
  --cert-identity 'https://github.com/sftwnd/bip39-morse/.github/workflows/release-pypi.yml@refs/tags/v1.0.2' \
  --cert-oidc-issuer 'https://token.actions.githubusercontent.com' \
  bip39-morse-1.0.2-py3-none-any.whl
```

Worth advertising this in release notes for big releases, especially security-sensitive ones.
