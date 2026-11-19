#!/usr/bin/env python3
"""deep-cleanup: Universal Agent-Agnostic Storage Bloat & Cache Cleaner.

A zero-dependency, production-grade cleanup engine designed for developers
and AI coding agents (Antigravity CLI, OpenCode, Claude Code, Gemini CLI).
Safely reclaims gigabytes of disk space by clearing verified developer caches
and build bloat while strictly enforcing user-defined protection allowlists.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

VERSION = "1.0.0"

# Default configuration path
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "deep-cleanup"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "exemptions.json"

# Invariant: Root and critical system paths that can NEVER be deleted under any circumstance
SYSTEM_FORBIDDEN_ROOTS: Set[str] = {
    "/",
    "/root",
    "/home",
    "/usr",
    "/bin",
    "/sbin",
    "/etc",
    "/lib",
    "/lib64",
    "/var",
    "/proc",
    "/sys",
    "/dev",
    "/boot",
    "/storage",
    "/sdcard",
    str(Path.home().resolve()),
}

# Default shell and identity files always preserved unless explicitly configured otherwise
DEFAULT_PROTECTED_FILENAMES: Set[str] = {
    ".bashrc",
    ".bash_profile",
    ".profile",
    ".zshrc",
    ".gitconfig",
    "authorized_keys",
    "id_rsa",
    "id_ed25519",
}


def get_default_config() -> Dict[str, Any]:
    """Return default clean configuration template with zero personal entries."""
    return {
        "version": VERSION,
        "protected_tools": [],
        "protected_paths": [],
        "protected_skills": [],
        "cleaning_targets": {
            "npm_cache": True,
            "pnpm_cache": True,
            "yarn_cache": True,
            "bun_cache": True,
            "pip_cache": True,
            "uv_cache": True,
            "cargo_cache": True,
            "gradle_cache": True,
            "go_cache": True,
            "system_tmp": True,
            "playwright_cache": False,
            "build_artifacts": False,
        },
        "custom_clean_paths": [],
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def format_bytes(size: int) -> str:
    """Format bytes into human-readable string."""
    if size < 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} B"
        size /= 1024.0
    return f"{size:.1f} PB"


def get_dir_size(path: Path) -> int:
    """Calculate total size of a file or directory in bytes safely and quickly."""
    try:
        if path.is_symlink():
            return 0
        if path.is_file():
            return path.stat().st_size

        # Fast path using du (vastly faster in Linux/PRoot/macOS)
        try:
            res = subprocess.run(["du", "-sk", str(path)], capture_output=True, text=True, timeout=2.0)
            if res.returncode == 0 and res.stdout.strip():
                first_line = res.stdout.strip().splitlines()[0]
                kb = int(first_line.split()[0])
                return kb * 1024
        except Exception:
            pass

        total = 0
        for root, dirs, files in os.walk(str(path)):
            for f in files:
                try:
                    fp = os.path.join(root, f)
                    if not os.path.islink(fp):
                        total += os.path.getsize(fp)
                except OSError:
                    continue
        return total
    except Exception:
        return 0


def get_disk_usage(path: str = "/") -> Dict[str, str]:
    """Retrieve filesystem disk usage for path."""
    try:
        res = subprocess.run(["df", "-h", path], capture_output=True, text=True, timeout=2.0)
        if res.returncode == 0:
            lines = res.stdout.strip().splitlines()
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 5:
                    return {
                        "filesystem": parts[0],
                        "size": parts[1],
                        "used": parts[2],
                        "avail": parts[3],
                        "use_pct": parts[4],
                    }
    except Exception:
        pass
    return {"filesystem": "unknown", "size": "N/A", "used": "N/A", "avail": "N/A", "use_pct": "N/A"}


class DeepCleanupEngine:
    """Universal Deep Cleanup orchestration engine."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.config: Dict[str, Any] = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from disk or return default template."""
        if self.config_path.is_file():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    defaults = get_default_config()
                    # Ensure nested dictionary keys exist
                    for k, v in defaults.items():
                        if k not in data:
                            data[k] = v
                        elif isinstance(v, dict) and isinstance(data[k], dict):
                            for sub_k, sub_v in v.items():
                                if sub_k not in data[k]:
                                    data[k][sub_k] = sub_v
                    return data
            except Exception as e:
                sys.stderr.write(f"Warning: Failed to parse {self.config_path}: {e}. Using defaults.\n")
        return get_default_config()

    def save_config(self) -> None:
        """Save active configuration to disk atomically."""
        self.config["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.config_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2)
        tmp_path.replace(self.config_path)

    def is_configured(self) -> bool:
        """Check if configuration file exists on disk."""
        return self.config_path.is_file()

    def is_path_forbidden(self, path: Path) -> Tuple[bool, str]:
        """Check if path violates system invariants."""
        try:
            resolved = str(path.resolve())
        except Exception:
            resolved = str(path)

        if resolved in SYSTEM_FORBIDDEN_ROOTS:
            return True, f"Matches forbidden root system path: {resolved}"

        # Cannot delete root filesystem or home top-level
        if resolved == "/" or resolved == str(Path.home().resolve()):
            return True, "Cannot delete root or user home directory"

        return False, ""

    def is_protected(self, target: Path | str) -> Tuple[bool, str]:
        """Check if a path or target is protected by user allowlist or system invariants."""
        p = Path(target) if isinstance(target, str) else target
        forbidden, reason = self.is_path_forbidden(p)
        if forbidden:
            return True, reason

        name = p.name.lower()
        if name in DEFAULT_PROTECTED_FILENAMES:
            return True, f"Protected default configuration file: {p.name}"

        # 1. Check protected_tools
        protected_tools = {str(t).strip().lower() for t in self.config.get("protected_tools", []) if str(t).strip()}
        if name in protected_tools or str(target).strip().lower() in protected_tools:
            return True, f"Explicitly protected in user allowlist (tool: {target})"

        for tool in protected_tools:
            if tool and (tool == name or tool in p.parts):
                return True, f"Matches protected tool allowlist entry: '{tool}'"

        # 2. Check protected_paths
        try:
            resolved_p = str(p.resolve())
        except Exception:
            resolved_p = str(p)

        protected_paths = self.config.get("protected_paths", [])
        for prot_p in protected_paths:
            prot_str = str(prot_p).strip()
            if not prot_str:
                continue
            # Match path basename case-insensitively for tool names
            if Path(prot_str).name.lower() == name or prot_str.lower() == name:
                return True, f"Matches protected path basename: {prot_p}"

            try:
                resolved_prot = str(Path(prot_str).expanduser().resolve())
            except Exception:
                resolved_prot = prot_str

            if resolved_p == resolved_prot:
                return True, f"Explicitly protected path: {prot_p}"
            # Also protect descendants of protected paths
            if resolved_p.startswith(resolved_prot.rstrip("/") + "/"):
                return True, f"Child of protected path: {prot_p}"

        # 3. Check protected_skills
        protected_skills = {str(s).strip().lower() for s in self.config.get("protected_skills", []) if str(s).strip()}
        if name in protected_skills:
            return True, f"Protected skill entry: {name}"

        return False, ""

    def add_protection(self, name_or_path: str) -> Dict[str, Any]:
        """Add a tool, skill, or path permanently to the protected allowlist."""
        item = name_or_path.strip()
        if not item:
            return {"success": False, "error": "Empty target provided"}

        p = Path(item).expanduser()
        if p.is_absolute() or "/" in item:
            paths = self.config.setdefault("protected_paths", [])
            item_canon = str(p.resolve()) if p.exists() else str(p)
            if item_canon not in paths and item not in paths:
                paths.append(item)
                self.save_config()
                return {"success": True, "action": "protected_path", "target": item, "config_file": str(self.config_path)}
            return {"success": True, "action": "already_protected", "target": item}

        # Check if it looks like a skill or tool
        tools = self.config.setdefault("protected_tools", [])
        if item not in tools:
            tools.append(item)
            self.save_config()
            return {"success": True, "action": "protected_tool", "target": item, "config_file": str(self.config_path)}

        return {"success": True, "action": "already_protected", "target": item}

    def remove_protection_or_target(self, target: str) -> Dict[str, Any]:
        """If target is in allowlist, remove protection. Otherwise clean the target."""
        item = target.strip()
        item_lower = item.lower()
        modified = False

        # 1. Check tools
        tools = self.config.get("protected_tools", [])
        new_tools = [t for t in tools if t.strip().lower() != item_lower]
        if len(new_tools) != len(tools):
            self.config["protected_tools"] = new_tools
            modified = True

        # 2. Check paths
        paths = self.config.get("protected_paths", [])
        new_paths = [p for p in paths if p.strip().lower() != item_lower and Path(p).name.lower() != item_lower]
        if len(new_paths) != len(paths):
            self.config["protected_paths"] = new_paths
            modified = True

        # 3. Check skills
        skills = self.config.get("protected_skills", [])
        new_skills = [s for s in skills if s.strip().lower() != item_lower]
        if len(new_skills) != len(skills):
            self.config["protected_skills"] = new_skills
            modified = True

        if modified:
            self.save_config()
            return {
                "success": True,
                "action": "unprotected",
                "message": f"Successfully removed '{item}' from protected allowlist in {self.config_path}",
                "target": item,
            }

        # Target is not protected: attempt safe removal if it exists on disk
        target_path = Path(item).expanduser()
        if target_path.exists():
            prot, reason = self.is_protected(target_path)
            if prot:
                return {
                    "success": False,
                    "error": f"Cannot remove '{item}': {reason}",
                }
            size = get_dir_size(target_path)
            try:
                if target_path.is_file() or target_path.is_symlink():
                    target_path.unlink()
                else:
                    shutil.rmtree(target_path)
                return {
                    "success": True,
                    "action": "deleted_target",
                    "target": str(target_path),
                    "reclaimed_bytes": size,
                    "reclaimed_human": format_bytes(size),
                }
            except Exception as e:
                return {"success": False, "error": f"Failed to delete {target_path}: {e}"}

        return {
            "success": False,
            "error": f"'{item}' was not found in protected allowlist, nor does it exist as a local path to clean.",
        }

    def discover_cache_targets(self) -> List[Dict[str, Any]]:
        """Discover active cache directories based on configuration."""
        home = Path.home()
        targets_cfg = self.config.get("cleaning_targets", {})
        discovered: List[Dict[str, Any]] = []

        candidate_definitions = [
            ("npm_cache", "NPM Cache & Logs", [home / ".npm" / "_cacache", home / ".npm" / "_logs"]),
            ("pnpm_cache", "PNPM Cache", [home / ".local" / "share" / "pnpm" / "store", home / ".cache" / "pnpm"]),
            ("yarn_cache", "Yarn Cache", [home / ".cache" / "yarn", home / ".yarn" / "berry" / "cache"]),
            ("bun_cache", "Bun Cache", [home / ".bun" / "install" / "cache"]),
            ("pip_cache", "Pip Wheel Cache", [home / ".cache" / "pip", home / ".cache" / "pipenv"]),
            ("uv_cache", "UV Cache", [home / ".cache" / "uv", home / ".local" / "share" / "uv"]),
            ("cargo_cache", "Cargo Cache", [home / ".cargo" / "registry" / "cache", home / ".cargo" / "git" / "db"]),
            ("gradle_cache", "Gradle Caches", [home / ".gradle" / "caches", home / ".gradle" / "daemon"]),
            ("go_cache", "Go Build Cache", [home / ".cache" / "go-build", home / "go" / "pkg" / "mod" / "cache"]),
            ("playwright_cache", "Playwright Browsers", [home / ".cache" / "ms-playwright"]),
        ]

        for target_key, label, paths in candidate_definitions:
            if not targets_cfg.get(target_key, False):
                continue
            for p in paths:
                if p.exists():
                    is_prot, reason = self.is_protected(p)
                    size = 0 if is_prot else get_dir_size(p)
                    discovered.append({
                        "id": target_key,
                        "label": label,
                        "path": str(p),
                        "exists": True,
                        "size_bytes": size,
                        "size_human": format_bytes(size),
                        "protected": is_prot,
                        "reason": reason,
                    })

        # User temporary files in /tmp
        if targets_cfg.get("system_tmp", False):
            tmp_dir = Path("/tmp")
            if tmp_dir.exists():
                user_tmp_bytes = 0
                user_tmp_items = 0
                uid = os.getuid() if hasattr(os, "getuid") else -1
                now = datetime.datetime.now().timestamp()
                try:
                    for entry in os.scandir(tmp_dir):
                        try:
                            # Only target files/dirs owned by current user older than 12 hours
                            st = entry.stat()
                            if uid != -1 and st.st_uid != uid:
                                continue
                            if (now - st.st_mtime) < 43200:
                                continue
                            p = Path(entry.path)
                            is_prot, _ = self.is_protected(p)
                            if not is_prot:
                                if entry.is_file() or entry.is_symlink():
                                    sz = st.st_size
                                else:
                                    sz = get_dir_size(p)
                                user_tmp_bytes += sz
                                user_tmp_items += 1
                        except (PermissionError, FileNotFoundError, OSError):
                            continue
                except Exception:
                    pass

                if user_tmp_items > 0:
                    discovered.append({
                        "id": "system_tmp",
                        "label": "User Temporary Files (/tmp)",
                        "path": "/tmp (stale user files >12h)",
                        "exists": True,
                        "size_bytes": user_tmp_bytes,
                        "size_human": format_bytes(user_tmp_bytes),
                        "protected": False,
                        "reason": "",
                        "is_tmp_collection": True,
                    })

        # Custom user clean paths
        for custom_p in self.config.get("custom_clean_paths", []):
            cp = Path(custom_p).expanduser()
            if cp.exists():
                is_prot, reason = self.is_protected(cp)
                size = 0 if is_prot else get_dir_size(cp)
                discovered.append({
                    "id": "custom_path",
                    "label": f"Custom Clean Target: {cp.name}",
                    "path": str(cp),
                    "exists": True,
                    "size_bytes": size,
                    "size_human": format_bytes(size),
                    "protected": is_prot,
                    "reason": reason,
                })

        return discovered

    def run_cleanup(self, dry_run: bool = True) -> Dict[str, Any]:
        """Execute audit or cleanup of all discovered targets."""
        before_disk = get_disk_usage(str(Path.home()))
        targets = self.discover_cache_targets()

        processed_targets = []
        total_reclaimed_bytes = 0

        for t in targets:
            path_str = t["path"]
            if t.get("protected"):
                processed_targets.append({
                    "id": t["id"],
                    "label": t["label"],
                    "path": path_str,
                    "status": "SKIPPED_PROTECTED",
                    "reason": t.get("reason"),
                    "reclaimed_bytes": 0,
                    "reclaimed_human": "0 B",
                })
                continue

            size = t["size_bytes"]
            if dry_run:
                processed_targets.append({
                    "id": t["id"],
                    "label": t["label"],
                    "path": path_str,
                    "status": "WOULD_CLEAN",
                    "size_bytes": size,
                    "size_human": format_bytes(size),
                })
                total_reclaimed_bytes += size
            else:
                # Execution mode
                clean_success = False
                error_msg = ""
                try:
                    if t.get("is_tmp_collection"):
                        # Clean individual stale user files in /tmp
                        uid = os.getuid() if hasattr(os, "getuid") else -1
                        now = datetime.datetime.now().timestamp()
                        for entry in os.scandir(Path("/tmp")):
                            try:
                                st = entry.stat()
                                if uid != -1 and st.st_uid != uid:
                                    continue
                                if (now - st.st_mtime) < 43200:
                                    continue
                                ep = Path(entry.path)
                                is_p, _ = self.is_protected(ep)
                                if not is_p:
                                    if ep.is_file() or ep.is_symlink():
                                        ep.unlink()
                                    elif ep.is_dir():
                                        shutil.rmtree(ep)
                            except Exception:
                                continue
                        clean_success = True
                    else:
                        target_p = Path(path_str)
                        if target_p.exists():
                            if target_p.is_file() or target_p.is_symlink():
                                target_p.unlink()
                            elif target_p.is_dir():
                                shutil.rmtree(target_p)
                                # Re-create empty directory for caches that expect parent structure
                                target_p.mkdir(parents=True, exist_ok=True)
                            clean_success = True
                except Exception as e:
                    clean_success = False
                    error_msg = str(e)

                if clean_success:
                    total_reclaimed_bytes += size
                    processed_targets.append({
                        "id": t["id"],
                        "label": t["label"],
                        "path": path_str,
                        "status": "CLEANED",
                        "reclaimed_bytes": size,
                        "reclaimed_human": format_bytes(size),
                    })
                else:
                    processed_targets.append({
                        "id": t["id"],
                        "label": t["label"],
                        "path": path_str,
                        "status": "ERROR",
                        "error": error_msg,
                        "reclaimed_bytes": 0,
                        "reclaimed_human": "0 B",
                    })

        # Also trigger CLI tool cache cleaners if binaries exist and caches are enabled
        if not dry_run:
            targets_cfg = self.config.get("cleaning_targets", {})
            if targets_cfg.get("bun_cache", False) and shutil.which("bun"):
                try:
                    subprocess.run(["bun", "pm", "cache", "rm"], capture_output=True, timeout=10)
                except Exception:
                    pass
            if targets_cfg.get("uv_cache", False) and shutil.which("uv"):
                try:
                    subprocess.run(["uv", "cache", "clean"], capture_output=True, timeout=10)
                except Exception:
                    pass

        after_disk = get_disk_usage(str(Path.home()))

        return {
            "mode": "DRY_RUN" if dry_run else "EXECUTE",
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "config_file": str(self.config_path),
            "protected_summary": {
                "tools_count": len(self.config.get("protected_tools", [])),
                "paths_count": len(self.config.get("protected_paths", [])),
                "skills_count": len(self.config.get("protected_skills", [])),
            },
            "targets": processed_targets,
            "total_reclaimed_bytes": total_reclaimed_bytes,
            "total_reclaimed_human": format_bytes(total_reclaimed_bytes),
            "storage": {
                "before": before_disk,
                "after": after_disk,
            },
        }


def run_interactive_onboarding(engine: DeepCleanupEngine) -> None:
    """Guide the user through first-run interactive configuration."""
    print("=" * 64)
    print("  🚀 Welcome to Deep Cleanup (/deep-cleanup) Setup")
    print("=" * 64)
    print("\nDeep Cleanup protects your critical development tools, agent skills,")
    print("and project directories while reclaiming gigabytes of cache bloat.\n")

    # 1. Ask for protected tools / directories / skills
    print("1. [PROTECTED ALLOWLIST] What tools, skills, or folders must NEVER be deleted?")
    print("   Enter names or paths separated by commas (e.g. 'my-app, ~/.ssh, my-custom-skill'):")
    try:
        user_input = input("   > ").strip()
    except (EOFError, KeyboardInterrupt):
        user_input = ""

    protected_tools = []
    protected_paths = []
    if user_input:
        for item in user_input.split(","):
            val = item.strip()
            if not val:
                continue
            if "/" in val:
                protected_paths.append(val)
            else:
                protected_tools.append(val)

    # 2. Ask for cache targets to clean
    print("\n2. [CLEANUP TARGETS] Which caches do you want /deep-cleanup to clear?")
    print("   Recommended defaults: npm, pnpm, bun, pip, uv, cargo, gradle, go, tmp.")
    print("   Press ENTER to accept all recommended defaults, or type specific ones to enable:")
    try:
        cache_input = input("   [ALL/defaults] > ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        cache_input = ""

    config = get_default_config()
    config["protected_tools"] = protected_tools
    config["protected_paths"] = protected_paths

    if cache_input and cache_input not in ("all", "default", "defaults", "y", "yes"):
        # Custom selection
        targets = config["cleaning_targets"]
        for k in targets.keys():
            targets[k] = False
        for tok in cache_input.replace(",", " ").split():
            clean_tok = tok.strip()
            for k in targets.keys():
                if clean_tok in k:
                    targets[k] = True

    engine.config = config
    engine.save_config()

    print("\n" + "=" * 64)
    print(f"✔ Configuration successfully created at: {engine.config_path}")
    print(f"✔ Protected items saved: {len(protected_tools) + len(protected_paths)}")
    print("=" * 64 + "\n")


def print_markdown_report(result: Dict[str, Any]) -> None:
    """Format and print results as clean Markdown."""
    mode = result["mode"]
    reclaimed = result["total_reclaimed_human"]
    storage = result["storage"]
    avail_after = storage["after"].get("avail", "N/A")
    avail_before = storage["before"].get("avail", "N/A")

    print(f"# Deep Cleanup Report ({mode})\n")
    print(f"> **Mode:** `{mode}`  ")
    print(f"> **Total Space Reclaimable:** **{reclaimed}**  ")
    print(f"> **Disk Available:** `{avail_after}` (was `{avail_before}`)\n")

    print("## Target Breakdown\n")
    print("| Target / Cache | Path | Status / Action | Size |")
    print("| :--- | :--- | :---: | :---: |")

    for t in result["targets"]:
        status = t.get("status", "UNKNOWN")
        sz = t.get("size_human", t.get("reclaimed_human", "0 B"))
        path_str = t.get("path", "")
        if len(path_str) > 40:
            path_str = "..." + path_str[-37:]

        if status == "CLEANED":
            badge = "✔ Cleaned"
        elif status == "WOULD_CLEAN":
            badge = "🔍 Ready to Clean"
        elif status == "SKIPPED_PROTECTED":
            badge = f"🛡️ Protected ({t.get('reason', 'allowlist')})"
        else:
            badge = f"❌ {status}"

        print(f"| **{t['label']}** | `{path_str}` | {badge} | {sz} |")

    print("\n## Safety & Configuration Summary")
    summary = result.get("protected_summary", {})
    print(f"* **Protected Tools:** {summary.get('tools_count', 0)}")
    print(f"* **Protected Paths:** {summary.get('paths_count', 0)}")
    print(f"* **Protected Skills:** {summary.get('skills_count', 0)}")
    print(f"* **Config File:** `{result.get('config_file')}`\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deep Cleanup: Universal Agent-Agnostic Storage & Cache Purge Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="Path to exemptions config")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Simulate cleanup without changes")
    parser.add_argument("--execute", action="store_true", default=False, help="Execute cleanup")
    parser.add_argument("--init", action="store_true", help="Launch interactive first-run onboarding")
    parser.add_argument("--init-defaults", action="store_true", help="Initialize config with standard defaults")
    parser.add_argument("--protect", type=str, metavar="NAME_OR_PATH", help="Permanently protect a tool, skill, or path")
    parser.add_argument("--unprotect", type=str, metavar="NAME_OR_PATH", help="Remove an entry from the protected allowlist")
    parser.add_argument("--remove", type=str, metavar="NAME_OR_PATH", help="Unprotect allowlist entry or clean target path")
    parser.add_argument("--list", action="store_true", help="List all protected items and targets")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    args = parser.parse_args()
    engine = DeepCleanupEngine(config_path=args.config)

    # 1. Protection addition
    if args.protect:
        res = engine.add_protection(args.protect)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            if res["success"]:
                print(f"✔ Successfully protected '{args.protect}'. Added to {engine.config_path}")
            else:
                print(f"❌ Error: {res.get('error')}", file=sys.stderr)
        return 0 if res["success"] else 1

    # 2. Unprotect or remove
    if args.unprotect or args.remove:
        target = args.unprotect or args.remove
        res = engine.remove_protection_or_target(target)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            if res["success"]:
                msg = res.get("message")
                if not msg:
                    reclaimed = res.get("reclaimed_human", "")
                    msg = f"Removed {target} ({reclaimed})" if reclaimed else f"Removed {target}"
                print(f"✔ {msg}")
            else:
                print(f"❌ Error: {res.get('error')}", file=sys.stderr)
        return 0 if res["success"] else 1

    # 3. List
    if args.list:
        if args.json:
            print(json.dumps(engine.config, indent=2))
        else:
            print(f"Configuration file: {engine.config_path}")
            print(f"Protected Tools:  {engine.config.get('protected_tools', [])}")
            print(f"Protected Paths:  {engine.config.get('protected_paths', [])}")
            print(f"Protected Skills: {engine.config.get('protected_skills', [])}")
            print("\nCleaning Targets:")
            for k, v in engine.config.get("cleaning_targets", {}).items():
                print(f"  - {k}: {'ENABLED' if v else 'disabled'}")
        return 0

    # 4. Interactive or default onboarding
    if args.init:
        run_interactive_onboarding(engine)
        return 0

    if args.init_defaults:
        engine.config = get_default_config()
        engine.save_config()
        if args.json:
            print(json.dumps({"success": True, "config_file": str(engine.config_path)}, indent=2))
        else:
            print(f"✔ Initialized default configuration at {engine.config_path}")
        return 0

    # 5. First-run auto-check
    if not engine.is_configured() and not args.json:
        if sys.stdin.isatty():
            run_interactive_onboarding(engine)
        else:
            # Running in non-interactive environment (e.g. agent pipe)
            print("Notice: No configuration found at ~/.config/deep-cleanup/exemptions.json.")
            print("Initializing default configuration with empty protected allowlist.")
            engine.config = get_default_config()
            engine.save_config()

    # 6. Default execution (dry-run unless --execute specified)
    is_dry_run = not args.execute
    result = engine.run_cleanup(dry_run=is_dry_run)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_markdown_report(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
