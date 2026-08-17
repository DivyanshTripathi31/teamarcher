#!/usr/bin/env python3
"""Manual end-to-end production verification for Team Archer.

Run on EC2 through the local Nginx proxy. Passwords and bearer tokens stay in
process memory only. A uniquely named, one-file presentation is created solely
for verification and is deleted (including its private S3 object) before exit.
"""
from __future__ import annotations

import json
import secrets
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from getpass import getpass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree


API_BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1/api").rstrip("/")


def request(path: str, method: str = "GET", body: dict | None = None, token: str | None = None, data: bytes | None = None, content_type: str | None = None, extra_headers: dict[str, str] | None = None) -> tuple[int, dict]:
    payload = data if data is not None else (json.dumps(body).encode() if body is not None else None)
    headers = {"Accept": "application/json", **(extra_headers or {})}
    if data is None and body is not None:
        headers["Content-Type"] = "application/json"
    elif content_type:
        headers["Content-Type"] = content_type
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(f"{API_BASE}{path}", data=payload, headers=headers, method=method)
    try:
        with urlopen(req, timeout=20) as response:
            raw = response.read()
            try:
                return response.status, json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return response.status, {}
    except HTTPError as error:
        raw = error.read()
        try:
            return error.code, json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return error.code, {}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAILED: {message}")
    print(f"PASS: {message}")


def login(username: str, password: str, expected: int) -> dict:
    status, data = request("/auth/login", method="POST", body={"username": username, "password": password})
    require(status == expected, f"login returned HTTP {expected}")
    return data


def multipart_upload(fields: dict[str, str], filename: str, payload: bytes) -> tuple[bytes, str]:
    boundary = f"----TeamArcherPhase5{secrets.token_hex(12)}"
    lines: list[bytes] = []
    for key, value in fields.items():
        lines.extend((f"--{boundary}\r\n".encode(), f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(), value.encode(), b"\r\n"))
    lines.extend((f"--{boundary}\r\n".encode(), f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'.encode(), b"Content-Type: text/plain\r\n\r\n", payload, b"\r\n", f"--{boundary}--\r\n".encode()))
    return b"".join(lines), f"multipart/form-data; boundary={boundary}"


def wait_for_backend() -> None:
    for _ in range(20):
        status, data = request("/health")
        if status == 200 and data.get("status") == "ok":
            return
        time.sleep(1)
    raise SystemExit("FAILED: backend did not become ready after restart")


def download(url: str) -> tuple[int, bytes, str | None]:
    try:
        with urlopen(url, timeout=20) as response:
            return response.status, response.read(), None
    except HTTPError as error:
        body = error.read()
        code = None
        try:
            code = ElementTree.fromstring(body).findtext("{*}Code")
        except ElementTree.ParseError:
            pass
        host = urlparse(url).hostname or "unknown-host"
        detail = f"HTTP {error.code} from {host}" + (f" (S3 {code})" if code else "")
        return error.code, body, detail
    except URLError as error:
        return 0, b"", f"transport error while requesting {urlparse(url).hostname or 'unknown-host'}: {error.reason}"


def main() -> None:
    print(f"Testing production API through Nginx: {API_BASE}")
    status, _ = request("/admin/dashboard")
    require(status == 401, "unauthenticated protected API request is rejected with a frontend-readable error")

    status, _ = request("/auth/login", method="POST", body={"username": "PHASE5 INVALID", "password": "incorrect-password-verification-only"})
    require(status == 401, "incorrect login is rejected")

    status, _ = request("/auth/login", method="OPTIONS", extra_headers={"Origin": "https://divyanshtripathi31.github.io", "Access-Control-Request-Method": "POST"})
    require(status == 200, "configured GitHub Pages origin passes CORS preflight")

    admin_username = input("Changed-password ADMIN username [DIVYANSH TRIPATHI]: ").strip() or "DIVYANSH TRIPATHI"
    admin_password = getpass(f"Current password for {admin_username}: ")
    if not admin_password:
        raise SystemExit("An ADMIN password is required.")
    admin_login = login(admin_username, admin_password, 200)
    admin_token = admin_login.get("access_token", "")
    admin_user = admin_login.get("user", {})
    require(bool(admin_token) and admin_user.get("role") == "ADMIN", "ADMIN login returns a bearer token and ADMIN role")
    status, me = request("/auth/me", token=admin_token)
    require(status == 200 and me.get("username") == admin_user.get("username"), "/me returns the authenticated ADMIN identity")

    # Phase 3 tests the full temporary-password transition. Here we safely
    # verify the live flag before any write operation without changing a user.
    if admin_user.get("must_change_password"):
        status, _ = request("/presentations/999999/publish", method="POST", token=admin_token)
        require(status == 403, "must_change_password blocks publishing")
        raise SystemExit("Change this ADMIN password first, then rerun Phase 5 to perform the upload verification.")
    print("PASS: selected ADMIN has completed the password-change gate")

    instructor_username = input("INSTRUCTOR username [SUKHPAL SINGH]: ").strip() or "SUKHPAL SINGH"
    instructor_password = getpass(f"Current password for {instructor_username}: ")
    if not instructor_password:
        raise SystemExit("An INSTRUCTOR password is required.")
    instructor_login = login(instructor_username, instructor_password, 200)
    instructor_token = instructor_login.get("access_token", "")
    require(bool(instructor_token) and instructor_login.get("user", {}).get("role") == "INSTRUCTOR", "INSTRUCTOR login returns the expected role")
    status, _ = request("/admin/dashboard", token=instructor_token)
    require(status == 200, "INSTRUCTOR can access the permitted dashboard")

    status, site = request("/site-content")
    require(status == 200, "public site content is sourced from RDS")
    site_update = {"project_name": site["projectName"], "tagline": site["tagline"], "description": site["description"], "problem": site["problem"], "objectives": site["objectives"], "intended_users": site["intendedUsers"], "core_features": site["coreFeatures"], "roles": site["roles"]}
    status, _ = request("/admin/site-content", method="PATCH", body=site_update, token=instructor_token)
    require(status == 403, "INSTRUCTOR cannot edit ADMIN-only site content")

    marker = f"Team Archer Phase 5 verification {datetime.now(timezone.utc).isoformat()}".encode()
    suffix = secrets.token_hex(5)
    title = f"Phase 5 verification {suffix}"
    version = f"P5-{suffix}"
    fields = {"title": title, "version": version, "presentation_date": date.today().isoformat(), "authors": "Phase 5 verification", "change_summary": "Temporary end-to-end RDS and S3 verification.", "relative_paths": json.dumps(["phase5-verification.txt"])}
    payload, content_type = multipart_upload(fields, "phase5-verification.txt", marker)
    presentation_id: int | None = None
    file_url = ""
    try:
        status, created = request("/presentations/upload", method="POST", token=admin_token, data=payload, content_type=content_type)
        require(status == 201, "ADMIN upload creates RDS metadata and a private S3 object")
        presentation_id = created.get("id")
        require(isinstance(presentation_id, int), "upload returned a presentation identifier")
        status, _ = request(f"/presentations/{presentation_id}/publish", method="POST", token=admin_token)
        require(status == 200, "ADMIN can publish the uploaded collection")

        status, _ = request(f"/presentations/{presentation_id}", method="DELETE", token=instructor_token)
        require(status == 403, "INSTRUCTOR cannot delete an ADMIN-managed archive")

        subprocess.run(["sudo", "-n", "systemctl", "restart", "teamarcher-backend"], check=True)
        wait_for_backend()
        status, published = request(f"/presentations/{created['slug']}")
        require(status == 200, "published collection persists in RDS after service restart")
        asset = published.get("assets", [{}])[0]
        file_url = asset.get("file_url", "")
        download_url = asset.get("download_url", "")
        require(file_url.startswith("https://") and download_url.startswith("https://"), "private S3 reads use HTTPS presigned URLs")
        status, body, detail = download(file_url)
        require(status == 200 and body == marker, f"presigned preview URL retrieves the uploaded S3 object{f' ({detail})' if detail else ''}")
        status, body, detail = download(download_url)
        require(status == 200 and body == marker, f"presigned download URL retrieves the uploaded S3 object{f' ({detail})' if detail else ''}")

        status, records = request("/presentations")
        require(status == 200 and any(record.get("slug") == created["slug"] for record in records), "published archive entry is visible through the public API")

        status, _ = request(f"/presentations/{presentation_id}", method="DELETE", token=admin_token)
        require(status == 204, "ADMIN archive delete succeeds")
        presentation_id = None
        status, _ = request(f"/presentations/{created['slug']}")
        require(status == 404, "deleted archive metadata is no longer public")
        status, _, _ = download(file_url)
        require(status in {403, 404}, "deleted archive object is no longer retrievable with its former presigned URL")
    finally:
        if presentation_id is not None:
            status, _ = request(f"/presentations/{presentation_id}", method="DELETE", token=admin_token)
            print("PASS: cleaned up temporary verification archive" if status == 204 else f"WARNING: temporary verification archive cleanup returned HTTP {status}")

    print("PASS: Phase 5 verified real RDS persistence, private S3 upload/read/delete, and API authorization boundaries.")


if __name__ == "__main__":
    main()
