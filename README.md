# 🧹 Deep Cleanup (`/deep-cleanup`)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8+-green.svg)](https://python.org)
[![Agents: Universal](https://img.shields.io/badge/Agents-Antigravity%20|%20Claude%20Code%20|%20OpenCode%20|%20Gemini%20CLI-purple.svg)](https://github.com/spot0mee/deep-cleanup)

> **Universal, agent-agnostic storage bloat and cache cleaner with interactive onboarding, protected allowlists, and dynamic rule management.**

Modern software development rapidly consumes disk storage. Tools like **NPM, Bun, UV, Pip, Cargo, Gradle, Go, and Playwright** constantly accumulate gigabytes of caches, logs, and temporary artifacts. On laptops, cloud instances, and mobile PRoot environments, storage bloat degrades performance and causes build failures.

Traditional cleanup scripts are dangerous because they blindly wipe directories—often destroying your custom AI agent skills, critical repositories, SSH keys, or project configurations.

**Deep Cleanup (`/deep-cleanup`)** solves this:
- **Zero Personal Defaults**: Starts clean on any system with no hardcoded private paths or usernames.
- **Fail-Safe Protection**: Guarantees zero data loss for any tool, repository, or skill in your protected allowlist.
- **Interactive First-Run Onboarding**: Prompts you on first execution to define what to keep and what to clean.
- **Dynamic Rule Commands**: Add or remove protection on the fly via natural agent commands (`/deep-cleanup do not remove <name>`).
- **Universal Agent Portability**: Native support for **Antigravity CLI**, **OpenCode**, **Claude Code**, and **Gemini CLI**.

---

## ⚡ One-Shot Copy-Paste Setup Prompt

Want to install and configure `/deep-cleanup` right now? Just **copy and paste this prompt directly into your AI coding agent** (Antigravity CLI, OpenCode, Claude Code, or Gemini CLI):

```markdown
Install the universal `/deep-cleanup` skill into my environment:
1. Clone or fetch the `deep-cleanup` skill repository from https://github.com/spot0mee/deep-cleanup.git into ~/.agents/skills/deep-cleanup.
2. Create global symlinks so the skill is recognized across all agents:
   - ln -sfn ~/.agents/skills/deep-cleanup ~/.gemini/skills/deep-cleanup
   - ln -sfn ~/.agents/skills/deep-cleanup ~/.claude/skills/deep-cleanup
3. Verify that ~/.agents/skills/deep-cleanup/SKILL.md is in place.
4. Immediately launch the interactive first-run onboarding for `/deep-cleanup`: ask me which tools, directories, or skills I want to protect (never delete) and which developer caches to clean, then save my preferences into ~/.config/deep-cleanup/exemptions.json.
```

---

## 📋 Command Reference Table

| Slash Command / Invocation | Description | Example / Effect |
| :--- | :--- | :--- |
| **`/deep-cleanup`** | Audits cache bloat and runs a safe preview (`--dry-run`). Prompts for confirmation before executing. | Displays itemized manifest and reclaimable storage across all tools. |
| **`/deep-cleanup --execute`** | Cleans all enabled developer caches and stale temporary files while skipping everything in the protected allowlist. | Reclaims gigabytes of disk space and prints before/after stats. |
| **`/deep-cleanup do not remove <name>`** | Permanently adds `<name>` (tool, folder, skill, or path) to your local allowlist. Immune from all future deletions. | `/deep-cleanup do not remove my-app`<br>`/deep-cleanup do not remove ~/vault` |
| **`/deep-cleanup remove <name>`** | If `<name>` is in your allowlist, unprotects it. Otherwise safely cleans or purges the target directory. | `/deep-cleanup remove old-cache-dir`<br>`/deep-cleanup remove my-app` *(unprotects)* |
| **`/deep-cleanup list`** | Displays your active protected allowlist and enabled cache targets. | Shows contents of `~/.config/deep-cleanup/exemptions.json`. |

---

## 🔧 Prerequisites

### 1. Python 3.8+
`deep-cleanup` is built purely with the Python standard library. **Zero pip dependencies required**.

### 2. GitHub Authentication (For Clones & Contributions)
If cloning via GitHub CLI or managing private repositories:
```bash
# Authenticate GitHub CLI
gh auth login
```
Or ensure your SSH key is added:
```bash
ssh -T git@github.com
```

---

## 🚀 Manual Installation

If you prefer to install manually from the command line:

```bash
# 1. Clone the repository into your global agents directory
mkdir -p ~/.agents/skills
git clone --depth 1 https://github.com/spot0mee/deep-cleanup.git ~/.agents/skills/deep-cleanup

# 2. Make the engine script executable
chmod +x ~/.agents/skills/deep-cleanup/cleanup.py

# 3. Create agent symlinks (for Gemini CLI and Claude Code)
mkdir -p ~/.gemini/skills ~/.claude/skills
ln -sfn ~/.agents/skills/deep-cleanup ~/.gemini/skills/deep-cleanup
ln -sfn ~/.agents/skills/deep-cleanup ~/.claude/skills/deep-cleanup

# 4. Run interactive onboarding
python3 ~/.agents/skills/deep-cleanup/cleanup.py --init
```

---

## 🛡️ Interactive First-Run Onboarding

When you run `/deep-cleanup` for the very first time, the skill detects that no configuration file exists at `~/.config/deep-cleanup/exemptions.json`.

Instead of running blindly, your agent will pause and prompt you:

```text
================================================================
  🚀 Welcome to Deep Cleanup (/deep-cleanup) Setup
================================================================

1. [PROTECTED ALLOWLIST] What tools, skills, or folders must NEVER be deleted?
   Enter names or paths separated by commas (e.g. 'my-app, ~/.ssh, my-custom-skill'):
   > 

2. [CLEANUP TARGETS] Which caches do you want /deep-cleanup to clear?
   Recommended defaults: npm, pnpm, bun, pip, uv, cargo, gradle, go, tmp.
   Press ENTER to accept all recommended defaults:
   [ALL/defaults] > 
```

Your choices are automatically saved to `~/.config/deep-cleanup/exemptions.json`:

```json
{
  "version": "1.0.0",
  "protected_tools": ["my-app", "whisper-engine"],
  "protected_paths": ["~/.ssh", "~/code/production"],
  "protected_skills": ["custom-reviewer"],
  "cleaning_targets": {
    "npm_cache": true,
    "pnpm_cache": true,
    "yarn_cache": true,
    "bun_cache": true,
    "pip_cache": true,
    "uv_cache": true,
    "cargo_cache": true,
    "gradle_cache": true,
    "go_cache": true,
    "system_tmp": true,
    "playwright_cache": false,
    "build_artifacts": false
  }
}
```

---

## 📦 Supported Developer Caches

| Ecosystem | Targets Reclaimed | Mechanism |
| :--- | :--- | :--- |
| **Node.js / JS** | NPM (`_cacache`, `_logs`), Yarn cache, PNPM store | Direct purge & store cleanup |
| **Bun** | Bun package cache | Purges `~/.bun/install/cache` & `bun pm cache rm` |
| **Python** | Pip wheel cache, Pipenv cache | Purges `~/.cache/pip`, `~/.cache/pipenv` |
| **Astral UV** | UV wheel and binary cache | `uv cache clean` & `~/.cache/uv` |
| **Rust** | Cargo registry cache, git db | Purges `~/.cargo/registry/cache`, `~/.cargo/git/db` |
| **JVM / Android** | Gradle build cache & daemon logs | Purges `~/.gradle/caches`, `~/.gradle/daemon` |
| **Go** | Go build cache | Purges `~/.cache/go-build` |
| **System** | Temporary files in `/tmp` | Cleans stale files (>12h old) owned by user |
| **Playwright** | Chromium & browser downloads | Configurable via `playwright_cache` flag |

---

## 🔒 Safety Guarantees & Invariants

1. **System Protection Barrier**: Root filesystems (`/`, `/usr`, `/bin`, `/lib`, `/etc`, `/var`, `/home`, `$HOME`) can **never** be targeted or deleted.
2. **Path Hierarchy Immunity**: If `/home/user/projects` is protected, every subfolder and file inside it is automatically shielded.
3. **Fail-Closed on Ambiguity**: Any error resolving canonical paths or permission checks aborts the operation safely.
4. **Shell Configuration Safety**: Shell configuration files (`.bashrc`, `.zshrc`, `.profile`, `.gitconfig`, SSH keys) are immune from removal by default.

---

## 🧪 Running Tests

To verify safety and test the cleanup engine locally:

```bash
cd ~/.agents/skills/deep-cleanup
python3 -m unittest discover tests
```

---

## 📄 License

MIT © [spotOmee](https://github.com/spot0mee)
