"""Security, secret-redaction, and GitHub Actions workflow validation tests."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

from backend.utils.logger import redact_secrets


ROOT = Path(__file__).resolve().parent.parent


class TestSecurityAndWorkflows(unittest.TestCase):
    def test_log_redaction_strips_tokens_and_secrets(self) -> None:
        raw = "Authorization: Bearer ya29.a0AfH6SM_secret_token and key=AIzaSyDummySecretKey1234567890"
        cleaned = redact_secrets(raw, extra_secrets=["my_refresh_token_xyz"])
        self.assertNotIn("ya29.", cleaned)
        self.assertNotIn("AIzaSy", cleaned)
        self.assertIn("[REDACTED]", cleaned)

    def test_all_required_workflows_exist_and_parse_as_valid_yaml(self) -> None:
        required = [
            "generate-article.yml",
            "publish-article.yml",
            "scheduled-publishing.yml",
            "manual-bulk-publish.yml",
            "validate-project.yml",
            "deploy-pages.yml",
        ]
        wf_dir = ROOT / ".github" / "workflows"
        for name in required:
            path = wf_dir / name
            self.assertTrue(path.exists(), f"Missing required workflow: {name}")
            parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertIsInstance(parsed, dict)
            self.assertIn("permissions", parsed, f"Workflow {name} must define least-privilege permissions")
            self.assertIn("jobs", parsed)

    def test_no_hardcoded_secrets_in_frontend_or_data(self) -> None:
        secret_patterns = [
            re.compile(r"AIza[0-9A-Za-z\-_]{30,}"),
            re.compile(r"ya29\.[0-9A-Za-z\-_]{20,}"),
            re.compile(r"ghp_[0-9A-Za-z]{20,}"),
            re.compile(r"GOCSPX-[0-9A-Za-z\-_]{15,}"),
        ]
        for folder in [ROOT / "frontend" / "src", ROOT / "frontend" / "index.html", ROOT / "data"]:
            files = [folder] if folder.is_file() else [p for p in folder.rglob("*") if p.is_file()]
            for fp in files:
                content = fp.read_text(encoding="utf-8", errors="ignore")
                for pat in secret_patterns:
                    self.assertIsNone(pat.search(content), f"Potential hardcoded secret detected in {fp}")


if __name__ == "__main__":
    unittest.main()
