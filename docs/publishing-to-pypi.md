# Publishing to PyPI

This guide covers the complete PyPI publishing workflow — from creating a PyPI account to pushing version updates.

Inspectra uses **GitHub OIDC trusted publishing**, which means no API tokens to manage: GitHub authenticates to PyPI via OpenID Connect.

---

## Prerequisites

- A [GitHub](https://github.com) account
- A [PyPI](https://pypi.org) account
- Maintainer access to the `iamakashsoni/inspectra` repository
- The `publish.yml` workflow (already in `.github/workflows/`)

---

## Step 1 — Create a PyPI account

1. Go to [pypi.org/account/register](https://pypi.org/account/register/)
2. Sign up with your email and a strong password
3. **Enable two-factor authentication** (required since 2023):
   - Account settings → 2FA → set up TOTP (Google Authenticator, Authy, etc.)
   - Save recovery codes in a password manager

---

## Step 2 — Reserve the project name (first release only)

If this is the first release of `inspectra`:

1. Build the package locally:
   ```bash
   python -m pip install --upgrade build
   python -m build
   ```
   This creates `dist/inspectra-0.2.0-py3-none-any.whl` and `dist/inspectra-0.2.0.tar.gz`.

2. Create an API token for the initial upload:
   - PyPI → Account settings → API tokens → Add API token
   - Scope: "Entire account" (for the first upload only)
   - Copy the token (starts with `pypi-`) — you won't see it again

3. Upload to PyPI manually (one-time, to claim the name):
   ```bash
   python -m pip install --upgrade twine
   python -m twine upload dist/*
   ```
   - Username: `__token__`
   - Password: `pypi-...` (the token you just copied)

After the first release, all subsequent publishes go through GitHub Actions via OIDC — no API tokens needed.

---

## Step 3 — Configure trusted publishing on PyPI

This connects your GitHub repo to your PyPI project so GitHub Actions can publish without a token.

1. Go to [pypi.org](https://pypi.org) → your account → **Account settings** → **Publishing**
2. Scroll to **Add a new publisher**
3. Select **GitHub**
4. Fill in:
   - **PyPI Project Name:** `inspectra`
   - **Owner:** `iamakashsoni`
   - **Repository name:** `inspectra`
   - **Workflow filename:** `publish.yml`
   - **Environment name:** `pypi`
5. Click **Add**

PyPI now trusts publishes that come from `iamakashsoni/inspectra` via the `publish.yml` workflow running in the `pypi` environment.

---

## Step 4 — Create the `pypi` environment in GitHub

1. Go to your repo on GitHub
2. **Settings → Environments → New environment**
3. Name it `pypi` (must match what you entered on PyPI)
4. (Optional) Add required reviewers: under "Required reviewers", add yourself — this gives you a manual approve step before each publish
5. Save

---

## Step 5 — Verify the workflow file

Confirm `.github/workflows/publish.yml` exists and looks like this:

```yaml
name: Publish to PyPI

on:
  push:
    tags:
      - 'v*'   # Triggers on tags like v0.2.0, v1.0.0

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: pypi              # must match the environment from Step 4
    timeout-minutes: 10
    permissions:
      id-token: write              # required for OIDC trusted publishing
      contents: read
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 1
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: |
          python -m pip install --upgrade pip
          pip install build
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

---

## Step 6 — Publish your first release

1. Update the version in `pyproject.toml`:
   ```bash
   # For a patch release (0.2.0 → 0.2.1)
   sed -i 's/version = "0.2.0"/version = "0.2.1"/' pyproject.toml

   # For a minor release (0.2.1 → 0.3.0)
   sed -i 's/version = "0.2.1"/version = "0.3.0"/' pyproject.toml

   # For a major release (0.3.0 → 1.0.0)
   sed -i 's/version = "0.3.0"/version = "1.0.0"/' pyproject.toml
   ```

2. Update `CHANGELOG.md` with what changed under a new `[Unreleased]` → `[0.2.1]` heading.

3. Commit and tag:
   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "bump: v0.2.1"
   git tag v0.2.1
   git push origin main --tags
   ```

4. The tag push triggers the `publish.yml` workflow:
   - Go to the **Actions** tab to watch it run
   - If you added a required reviewer (Step 4), you'll get a notification to approve
   - The workflow builds the package and uploads to PyPI via OIDC
   - No API token is used — GitHub authenticates via OIDC

5. Verify the release:
   - Go to [pypi.org/project/inspectra](https://pypi.org/project/inspectra/)
   - The new version should appear within a minute
   - Install it: `pip install inspectra==0.2.1`

---

## Step 7 — Create a GitHub Release (optional, recommended)

After the PyPI publish succeeds, create a GitHub Release for visibility:

1. Go to your repo → **Releases → Draft a new release**
2. **Choose a tag:** `v0.2.1` (the tag you pushed)
3. **Release title:** `v0.2.1`
4. **Description:** paste the changelog entry for this version
5. **Publish release**

---

## Pushing subsequent updates

For every future release, repeat Step 6:

```bash
# 1. Bump version
sed -i 's/version = "0.2.1"/version = "0.2.2"/' pyproject.toml

# 2. Update CHANGELOG.md with what's new

# 3. Commit, tag, push
git add pyproject.toml CHANGELOG.md
git commit -m "bump: v0.2.2"
git tag v0.2.2
git push origin main --tags

# 4. Watch the Actions tab — the publish workflow runs automatically
# 5. Verify on pypi.org/project/inspectra
```

---

## Version bumping rules (Semantic Versioning)

| Bump type | When to use | Example |
|-----------|-------------|---------|
| **Patch** (0.2.1 → 0.2.2) | Bug fixes, no new features | Fix inline comment posting |
| **Minor** (0.2.2 → 0.3.0) | New features, backward-compatible | Add a new provider |
| **Major** (0.3.0 → 1.0.0) | Breaking changes | Change CLI flag names |

---

## Yanking a bad release

If a release is broken but you don't want to delete it:

```bash
pip install twine
python -m twine yank inspectra==0.2.1
```

Yanked versions stay downloadable but don't show up in `pip install inspectra` (pip picks the latest non-yanked).

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Workflow does not have permissions` | Ensure `permissions: id-token: write` is in the workflow |
| `Environment 'pypi' not found` | Create the environment in GitHub repo Settings → Environments |
| `Publisher not configured` | Redo Step 3 on PyPI — check owner/repo/workflow name match exactly |
| `File already exists` | You can't re-upload the same version. Bump the version and try again. |
| Build fails | Run `python -m build` locally first to debug |
| Tag didn't trigger workflow | Ensure the tag starts with `v` (e.g. `v0.2.1`, not `0.2.1`) |
