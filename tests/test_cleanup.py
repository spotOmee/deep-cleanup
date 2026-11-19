#!/usr/bin/env python3
"""Unit tests for deep-cleanup core engine."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import cleanup


class TestDeepCleanup(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_deep_cleanup_")
        self.config_path = Path(self.test_dir) / "exemptions.json"
        self.engine = cleanup.DeepCleanupEngine(config_path=self.config_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_default_config_is_sanitized_and_clean(self):
        """Ensure default configuration contains ZERO personal tools or private paths."""
        cfg = cleanup.get_default_config()
        self.assertEqual(cfg["protected_tools"], [])
        self.assertEqual(cfg["protected_paths"], [])
        self.assertEqual(cfg["protected_skills"], [])
        self.assertIn("npm_cache", cfg["cleaning_targets"])

    def test_protect_tool_and_path(self):
        """Test adding tools and paths to the allowlist."""
        res_tool = self.engine.add_protection("my-awesome-tool")
        self.assertTrue(res_tool["success"])
        self.assertIn("my-awesome-tool", self.engine.config["protected_tools"])

        custom_path = str(Path(self.test_dir) / "important_data")
        res_path = self.engine.add_protection(custom_path)
        self.assertTrue(res_path["success"])
        self.assertIn(custom_path, self.engine.config["protected_paths"])

        # Reload from disk and verify persistence
        new_engine = cleanup.DeepCleanupEngine(config_path=self.config_path)
        self.assertIn("my-awesome-tool", new_engine.config["protected_tools"])
        self.assertIn(custom_path, new_engine.config["protected_paths"])

    def test_unprotect_allowlist_entry(self):
        """Test unprotecting an item removes it from the allowlist."""
        self.engine.add_protection("custom-service")
        self.assertIn("custom-service", self.engine.config["protected_tools"])

        res = self.engine.remove_protection_or_target("custom-service")
        self.assertTrue(res["success"])
        self.assertEqual(res["action"], "unprotected")
        self.assertNotIn("custom-service", self.engine.config["protected_tools"])

    def test_system_forbidden_roots_immunity(self):
        """Verify root, home, and system paths can never be deleted."""
        for forbidden in ["/", "/root", "/home", "/usr", "/etc"]:
            prot, reason = self.engine.is_protected(Path(forbidden))
            self.assertTrue(prot, f"Expected {forbidden} to be protected")
            self.assertIn("forbidden", reason.lower())

    def test_target_protection_prevents_deletion(self):
        """Verify protected items cannot be cleaned via remove."""
        protected_file = Path(self.test_dir) / "vault" / "secret.key"
        protected_file.parent.mkdir(parents=True, exist_ok=True)
        protected_file.write_text("secret")

        self.engine.add_protection(str(protected_file))

        res = self.engine.remove_protection_or_target(str(protected_file))
        # First removal unprotects it
        self.assertTrue(res["success"])
        self.assertEqual(res["action"], "unprotected")
        self.assertTrue(protected_file.exists())

    def test_dry_run_does_not_delete(self):
        """Verify dry-run mode discovers items without mutating the filesystem."""
        fake_cache = Path(self.test_dir) / ".npm" / "_cacache"
        fake_cache.mkdir(parents=True, exist_ok=True)
        (fake_cache / "item.bin").write_bytes(b"x" * 1024)

        # Disable global caches for isolated test and point custom clean path to fake cache
        self.engine.config["cleaning_targets"] = {}
        self.engine.config["custom_clean_paths"] = [str(fake_cache)]
        res = self.engine.run_cleanup(dry_run=True)

        self.assertEqual(res["mode"], "DRY_RUN")
        self.assertTrue((fake_cache / "item.bin").exists())
        self.assertGreater(res["total_reclaimed_bytes"], 0)


    def test_target_execution_cleans_unprotected(self):
        """Verify execution mode cleans unprotected custom target."""
        fake_cache = Path(self.test_dir) / "build_bloat"
        fake_cache.mkdir(parents=True, exist_ok=True)
        (fake_cache / "trash.tmp").write_bytes(b"data" * 100)

        self.engine.config["cleaning_targets"] = {}
        self.engine.config["custom_clean_paths"] = [str(fake_cache)]
        res = self.engine.run_cleanup(dry_run=False)

        self.assertEqual(res["mode"], "EXECUTE")
        # In cleanup, empty directory is recreated
        self.assertFalse((fake_cache / "trash.tmp").exists())
        self.assertTrue(fake_cache.exists())

    def test_case_insensitive_and_child_path_protection(self):
        """Verify case insensitivity and child path protection."""
        parent_dir = Path(self.test_dir) / "MyProject"
        child_file = parent_dir / "src" / "index.ts"
        child_file.parent.mkdir(parents=True, exist_ok=True)
        child_file.write_text("console.log('hello');")

        self.engine.add_protection(str(parent_dir))

        prot, reason = self.engine.is_protected(child_file)
        self.assertTrue(prot)
        self.assertIn("child of protected path", reason.lower())

        prot_tool, _ = self.engine.is_protected("myproject")
        self.assertTrue(prot_tool)


if __name__ == "__main__":
    unittest.main()
