---
name: deep-cleanup
description: Universal, agent-agnostic storage bloat and cache cleaner with interactive onboarding, protected allowlists, and dynamic rule management. Cleans npm, pnpm, yarn, bun, pip, uv, cargo, gradle, go, and system temporary bloat while strictly preserving all user-protected tools, skills, and paths.
---

# Deep Cleanup (`/deep-cleanup`)

Universal, agent-agnostic storage bloat and cache cleaner designed for developers and AI coding agents (**Antigravity CLI**, **OpenCode**, **Claude Code**, **Gemini CLI**).

It eliminates runaway developer cache bloat (NPM, PNPM, Bun, Pip, UV, Cargo, Gradle, Go, temporary artifacts) while guaranteeing **zero data loss** for user-protected tools, skills, and project directories.

---

## 1. Operational Invariants & Privacy Guardrails

1. **Zero Personal Defaults**: Clean public distribution with zero hardcoded private usernames, device paths, or personal allowlists. Every user starts with an empty, customizable configuration.
2. **Interactive First-Run Configuration**: If `~/.config/deep-cleanup/exemptions.json` does not exist, the agent **must pause** and prompt the user before deleting anything.
3. **Strict Allowlist Enforcement**: Any tool, folder, repository, or skill registered in the user's local `exemptions.json` is completely immune from modification or deletion.
4. **Cache-Only Targeting**: By default, only regenerable cache directories and stale temporary files are cleaned. Runtimes, shims, package binaries, git repositories, and shell configurations are strictly protected.
5. **System Root Boundary**: Absolute immunity for system root paths (`/`, `/usr`, `/bin`, `/lib`, `/etc`, `/var`, `/home`, `$HOME`).
6. **Dry-Run by Default**: Unless explicitly instructed to execute (`--execute` or `--force`), the agent displays a detailed manifest of proposed reclaimable space before applying mutations.

---

## 2. Configuration Architecture

All user preferences and allowlists are stored locally in:
`~/.config/deep-cleanup/exemptions.json`

### Configuration Schema

```json
{
  "version": "1.0.0",
  "protected_tools": [
    "my-service",
    "custom-agent-tool"
  ],
  "protected_paths": [
    "~/projects/active-app",
    "~/.ssh"
  ],
  "protected_skills": [
    "my-custom-skill"
  ],
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
  },
  "custom_clean_paths": [],
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

---

## 3. Command Workflows & Agent Protocols

### A. First-Run Interactive Onboarding

**Trigger**: User runs `/deep-cleanup` (or asks to clean system caches), and `~/.config/deep-cleanup/exemptions.json` does NOT exist.

**Agent Protocol**:
1. **Pause Execution**: Do not run cleanup immediately.
2. **Prompt the User**: Ask the user two questions:
   - **Protection (Allowlist)**: *"Which tools, directories, skills, or projects must NEVER be deleted?"* (e.g., active projects, custom skills, models, private data).
   - **Cleaning Targets**: *"Which developer caches do you want to clean?"* (defaults: npm, pnpm, bun, pip, uv, cargo, gradle, go, stale /tmp files).
3. **Persist Configuration**: Create `~/.config/deep-cleanup/exemptions.json` populated with the user's answers.
4. **Proceed to Dry-Run Preview**: Run a dry-run audit and present the reclaimable space report.

> **Helper Command**:
> The bundled engine can also initialize configuration directly:
> ```bash
> python3 cleanup.py --init
> ```

---

### B. Standard Cleanup (`/deep-cleanup`)

**Trigger**: User runs `/deep-cleanup` or `/deep-cleanup --dry-run` or `/deep-cleanup --execute`.

**Agent Protocol**:
1. Verify `~/.config/deep-cleanup/exemptions.json` exists. If not, trigger onboarding above.
2. Run audit / dry-run to discover active cache bloat and calculate reclaimable bytes:
   ```bash
   python3 cleanup.py --dry-run
   ```
3. Display the clean Markdown summary table showing:
   - Target name & path
   - Status (`Ready to Clean` vs `Protected (Allowlist)`)
   - Reclaimable size
4. If invoked with `--execute` or if the user confirms:
   ```bash
   python3 cleanup.py --execute
   ```
5. Report final reclaimed storage and updated filesystem availability.

---

### C. Dynamic Protection: `/deep-cleanup do not remove <name>`

**Trigger**: User enters `/deep-cleanup do not remove <name>`, `protect <name>`, or `keep <name>`.

**Agent Protocol**:
1. Identify whether `<name>` is a path (contains `/` or starts with `~`) or a tool/skill name.
2. Execute the engine's protection command:
   ```bash
   python3 cleanup.py --protect "<name>"
   ```
3. Confirm to the user:
   > ✔ **Protected:** Added `<name>` to `~/.config/deep-cleanup/exemptions.json`. It is permanently immune from all future cleanups.

---

### D. Dynamic Target Removal: `/deep-cleanup remove <name>`

**Trigger**: User enters `/deep-cleanup remove <name>` or `unprotect <name>`.

**Agent Protocol**:
1. Check if `<name>` is currently in `~/.config/deep-cleanup/exemptions.json` (under `protected_tools`, `protected_paths`, or `protected_skills`).
2. **Case 1: Target IS in the protected allowlist**:
   - Remove `<name>` from the allowlist using:
     ```bash
     python3 cleanup.py --unprotect "<name>"
     ```
   - Confirm to the user:
     > ✔ **Protection Removed:** `<name>` is no longer in your protected allowlist.
3. **Case 2: Target is NOT in the allowlist**:
   - Check if `<name>` exists as a local directory or cache target.
   - Run safe target removal:
     ```bash
     python3 cleanup.py --remove "<name>"
     ```
   - Confirm deletion and report reclaimed space.

---

## 4. CLI Execution Reference

The `cleanup.py` script included in this skill can be run directly via bash or by any AI agent:

```bash
# Preview reclaimable storage (dry-run, zero mutations)
python3 cleanup.py --dry-run

# Execute full cleanup
python3 cleanup.py --execute

# Add item to protected allowlist
python3 cleanup.py --protect "my-app"
python3 cleanup.py --protect "~/projects/my-app"

# Remove item from allowlist or clean specific target
python3 cleanup.py --remove "my-app"
python3 cleanup.py --unprotect "my-app"

# Display current configuration & protected items
python3 cleanup.py --list

# Output machine-readable JSON for automated agents
python3 cleanup.py --dry-run --json
```

---

## 5. Supported Cache Targets

| Target ID | Description | Default Paths / Mechanisms |
| :--- | :--- | :--- |
| `npm_cache` | NPM Cache & Logs | `~/.npm/_cacache`, `~/.npm/_logs` |
| `pnpm_cache` | PNPM Store & Cache | `~/.local/share/pnpm/store`, `~/.cache/pnpm` |
| `yarn_cache` | Yarn Berry & v1 Cache | `~/.cache/yarn`, `~/.yarn/berry/cache` |
| `bun_cache` | Bun Package Cache | `bun pm cache rm`, `~/.bun/install/cache` |
| `pip_cache` | Python Pip & Pipenv | `~/.cache/pip`, `~/.cache/pipenv` |
| `uv_cache` | Astral UV Wheel Cache | `uv cache clean`, `~/.cache/uv` |
| `cargo_cache` | Rust Cargo Registry Cache | `~/.cargo/registry/cache`, `~/.cargo/git/db` |
| `gradle_cache` | Gradle Build Caches | `~/.gradle/caches`, `~/.gradle/daemon` |
| `go_cache` | Go Build Cache | `~/.cache/go-build`, `~/go/pkg/mod/cache` |
| `system_tmp` | Stale User Temp Files | Stale files in `/tmp` owned by user (>12h old) |
| `playwright_cache` | Playwright Browsers | `~/.cache/ms-playwright` *(disabled by default)* |
| `build_artifacts` | Custom User Build Dirs | Configured via `custom_clean_paths` |
