import asyncio
import json
import sys
from io import BytesIO
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from fastapi import UploadFile

from app import main


def upload(name, contents):
    return UploadFile(filename=name, file=BytesIO(contents))


def engine_report(root):
    """A report shaped like the engine's output for files under the upload root."""
    source = f"{root}/src/main.rs"
    evidence = {
        "kind": "RoleCheck",
        "mechanism": "require_admin",
        "symbol": "require_admin",
        "file": source,
        "line": 10,
        "handler": "admin_users",
        "strength": "Strong",
    }
    payments = {
        "method": "GET",
        "path": "/api/admin/payments",
        "handler": "admin_payments",
        "file": source,
        "line": 87,
        "authorized": False,
        "authorization": [],
    }
    users = {
        "method": "GET",
        "path": "/api/admin/users",
        "handler": "admin_users",
        "file": source,
        "line": 10,
        "authorized": True,
        "authorization": [evidence],
    }
    return {
        "files_scanned": 2,
        "parse_errors": [f"{root}/src/broken.rs: cannot parse string into token stream"],
        "routes": [
            {
                "method": "GET",
                "path": "/api/admin/payments",
                "scope_prefix": "/api/admin",
                "handler": "admin_payments",
                "handler_path": "admin_payments",
                "handler_resolution": {"kind": "Local"},
                "authorization": [],
                "line": 87,
                "file": source,
            }
        ],
        "peer_groups": [{"id": "peer-group-001", "description": "GET static routes under /api/admin", "routes": [payments, users]}],
        "invariants": [],
        "findings": [
            f"  Suspicious route: GET /api/admin/payments ({source}:87)\n"
            f"    - GET /api/admin/users\n"
            f"      RoleCheck: require_admin at {source}:10 (Strong)"
        ],
        "finding_details": [
            {
                "peer_group_id": "peer-group-001",
                "invariant": {},
                "suspicious_route": payments,
                "suspicious_route_evidence": [],
                "authorized_peer_routes": [users],
            }
        ],
    }


def fake_engine(command, **_kwargs):
    return SimpleNamespace(returncode=0, stdout=json.dumps(engine_report(command[2])), stderr="")


class ArcherReportPathTests(TestCase):
    user = SimpleNamespace(id=1, role="ADMIN", must_change_password=False)

    def analyze(self):
        settings = SimpleNamespace(archer_binary=sys.executable, max_upload_mb=50)
        with patch.object(main, "get_settings", return_value=settings), patch.object(main.subprocess, "run", side_effect=fake_engine):
            return asyncio.run(
                main.analyze_repository(
                    relative_paths=json.dumps(["Cargo.toml", "src/main.rs"]),
                    files=[upload("Cargo.toml", b"[package]\n"), upload("main.rs", b"fn main() {}\n")],
                    user=self.user,
                )
            )

    def test_finding_text_paths_are_relative_to_the_upload_root(self):
        finding = self.analyze()["findings"][0]

        self.assertIn("(src/main.rs:87)", finding)
        self.assertIn("require_admin at src/main.rs:10", finding)
        self.assertNotIn("/src/main.rs", finding)
        self.assertNotIn("archer-analysis-", finding)

    def test_structured_paths_and_parse_errors_are_unchanged(self):
        report = self.analyze()

        self.assertEqual(report["parse_errors"], ["src/broken.rs: cannot parse string into token stream"])
        self.assertEqual(report["routes"][0]["file"], "src/main.rs")
        self.assertEqual(report["routes"][0]["handler_resolution"], {"kind": "Local"})
        detail = report["finding_details"][0]
        self.assertEqual(detail["suspicious_route"]["file"], "src/main.rs")
        self.assertEqual(detail["authorized_peer_routes"][0]["authorization"][0]["file"], "src/main.rs")
        self.assertEqual(report["peer_groups"][0]["routes"][1]["authorization"][0]["file"], "src/main.rs")
        self.assertEqual(report["repository_files"], 2)
