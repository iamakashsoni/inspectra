# Self-Hosted Runner Setup

The Ollama workflow runs on a self-hosted runner — your own machine with Ollama installed. This keeps code fully private (never leaves your network) and is free (no API costs).

This guide covers the full setup from scratch.

---

## Prerequisites

- A machine that's always on (or wakes on PR events) — a home server, cloud VM, or office workstation
- Linux x86_64 (recommended), macOS, or Windows
- ≥16 GB RAM for 14B models, ≥32 GB for 32B models
- GPU optional but strongly recommended (Nvidia with CUDA, or Apple Silicon)
- Admin/sudo access for installing Ollama as a service

---

## Step 1 — Create the runner on GitHub

1. Go to your repository on GitHub
2. **Settings → Actions → Runners → New self-hosted runner**
3. Select your OS (Linux x64 for this guide)
4. GitHub shows a registration token — copy it (it's valid for ~1 hour)

---

## Step 2 — Install the runner software

On your runner machine:

```bash
# Create a directory for the runner
mkdir -p ~/actions-runner && cd ~/actions-runner

# Download the runner (check GitHub for the latest version)
curl -o actions-runner-linux-x64.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.317.0/actions-runner-linux-x64-2.317.0.tar.gz

# Extract
tar xzf actions-runner-linux-x64.tar.gz

# Configure — use the token from Step 1
./config.sh --url https://github.com/YOUR_ORG/YOUR_REPO --token YOUR_TOKEN

# When prompted:
# - Runner group: press Enter (default)
# - Runner name: inspectra-runner (or any name)
# - Labels: inspectra,ollama  (type these, press Enter after each, blank line to finish)
# - Work folder: press Enter (default _work)
```

---

## Step 3 — Install as a system service

This makes the runner start on boot and survive reboots:

```bash
sudo ./svc.sh install
sudo ./svc.sh start

# Verify it's running
sudo ./svc.sh status

# Check it shows as "Idle" (green) on GitHub:
# Settings → Actions → Runners → your runner should say "Idle"
```

To uninstall later: `sudo ./svc.sh stop && sudo ./svc.sh uninstall`

---

## Step 4 — Install Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Enable as a service (starts on boot, runs on port 11434)
sudo systemctl enable --now ollama

# Pull the review model (this takes a few minutes — ~8 GB download)
ollama pull qwen2.5-coder:14b

# Verify
ollama list
# Should show: qwen2.5-coder:14b

# Verify the API is reachable
curl http://localhost:11434/api/tags
# Should return JSON with the model list
```

---

## Step 5 — Add the workflow file

In your repository, create `.github/workflows/inspectra.yml` using the workflow from the [GitHub Actions](github-actions.md) guide (the "Self-hosted with Ollama" section).

---

## Step 6 — Test it

1. Open a pull request against your repository
2. Within a few seconds, the runner should pick up the `Inspectra Review (Ollama)` job
3. Check the Actions tab for logs
4. Once complete, the review appears as a comment on the PR

---

## Verification checklist

- [ ] Runner shows **Idle** (green) under Settings → Actions → Runners
- [ ] `curl http://localhost:11434/api/tags` returns JSON on the runner machine
- [ ] `ollama list` shows `qwen2.5-coder:14b`
- [ ] Opening a PR triggers the `Inspectra Review (Ollama)` workflow
- [ ] Review comment appears on the PR within ~2 minutes

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Runner shows "offline" | `sudo ./svc.sh status` on the runner machine; if stopped, `sudo ./svc.sh start` |
| Runner shows "offline" after reboot | Service not enabled: `sudo ./svc.sh install && sudo ./svc.sh start` |
| Ollama not reachable | `curl http://localhost:11434/api/tags` — if it fails, `sudo systemctl restart ollama` |
| Model not pulled | `ollama list` — if empty, `ollama pull qwen2.5-coder:14b` |
| Out of memory | Use a smaller model: `ollama pull qwen2.5-coder:7b`, update `--model` in workflow |
| GPU not used | `ollama ps` should show GPU — if CPU-only, install [CUDA](https://docs.nvidia.com/cuda/) |
| Workflow doesn't trigger | Check `paths-ignore` in the workflow — PRs touching only `.md`/docs are skipped |
| Review step fails but PR is open | `continue-on-error: true` is set — check the Actions logs for the error |
| First run is slow | Ollama loads the model into memory on first call (~30-60s). Subsequent calls are fast. |

---

## Updating the runner

```bash
cd ~/actions-runner
sudo ./svc.sh stop

# Download the new version (check GitHub for latest)
curl -o actions-runner-linux-x64.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.318.0/actions-runner-linux-x64-2.318.0.tar.gz
tar xzf actions-runner-linux-x64.tar.gz

sudo ./svc.sh start
```

---

## Updating Ollama models

```bash
# Update Ollama itself
curl -fsSL https://ollama.com/install.sh | sh

# Pull a newer model version
ollama pull qwen2.5-coder:14b   # re-pulls if there's an update

# Remove an old model to free disk
ollama rm qwen2.5-coder:7b
```

---

## Security notes

- The runner executes workflow code from your repository. Only register it on repos you trust.
- The `GITHUB_TOKEN` secret is automatically injected by GitHub Actions — you don't need to create it.
- Ollama listens on `localhost:11434` only (not exposed to the network) by default.
- Runner logs may contain diff content — store them securely if your repo is private.

---

## Multiple runners

You can register multiple machines as self-hosted runners for the same repo. GitHub automatically distributes jobs across available runners. This is useful for:

- **Redundancy** — if one runner is down, another picks up the job
- **Parallelism** — multiple PRs can be reviewed simultaneously
- **Different models** — label one runner `ollama-14b` and another `ollama-32b`, then use `runs-on: self-hosted, ollama-32b` in the workflow

To add a second runner, repeat Steps 1-3 on the new machine with a new registration token.
