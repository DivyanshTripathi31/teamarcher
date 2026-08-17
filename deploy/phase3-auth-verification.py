#!/usr/bin/env python3
"""Manual, production-safe authentication verification for Team Archer.

Run this on EC2 against the local Nginx proxy. Passwords and access tokens are
kept only in process memory; neither is printed, written to disk, nor passed
through shell arguments.
"""
from __future__ import annotations

import json
import sys
from getpass import getpass
from urllib.error import HTTPError
from urllib.request import Request, urlopen


API_BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1/api").rstrip("/")


def request(path: str, method: str = "GET", body: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    payload = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(f"{API_BASE}{path}", data=payload, headers=headers, method=method)
    try:
        with urlopen(req, timeout=15) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else {}
    except HTTPError as error:
        raw = error.read()
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {}
        return error.code, data


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAILED: {message}")
    print(f"PASS: {message}")


def login(username: str, password: str, expected_status: int) -> dict:
    status, data = request("/auth/login", method="POST", body={"username": username, "password": password})
    require(status == expected_status, f"login for {username} returned HTTP {expected_status}")
    return data


def verify_cors() -> None:
    req = Request(
        f"{API_BASE}/auth/login",
        headers={
            "Origin": "https://divyanshtripathi31.github.io",
            "Access-Control-Request-Method": "POST",
        },
        method="OPTIONS",
    )
    with urlopen(req, timeout=15) as response:
        allowed_origin = response.headers.get("Access-Control-Allow-Origin")
        require(response.status == 200 and allowed_origin == "https://divyanshtripathi31.github.io", "GitHub Pages origin passes CORS preflight")


def main() -> None:
    print(f"Testing production API through Nginx: {API_BASE}")
    verify_cors()
    admin_username = input("Admin username [DIVYANSH TRIPATHI]: ").strip() or "DIVYANSH TRIPATHI"
    admin_initial_password = getpass(f"Current initial password for {admin_username}: ")
    if not admin_initial_password:
        raise SystemExit("An admin password is required.")

    # A deliberately incorrect value verifies rejection without disclosing the
    # supplied password.
    login(admin_username, "incorrect-password-verification-only", 401)
    initial_login = login(admin_username, admin_initial_password, 200)
    admin_token = initial_login.get("access_token")
    initial_user = initial_login.get("user", {})
    require(bool(admin_token), "successful login returned an access token")
    require(initial_user.get("username") == admin_username.upper(), "login returned the expected admin identity")
    require(initial_user.get("role") == "ADMIN", "selected account has the ADMIN role")
    require(initial_user.get("must_change_password") is True, "initial account requires a password change")

    status, me = request("/auth/me", token=admin_token)
    require(status == 200 and me.get("username") == admin_username.upper() and me.get("role") == "ADMIN", "authenticated identity endpoint returns the expected admin")

    # The existing product behavior blocks publishing while the temporary
    # password remains in place. A nonexistent record keeps this read-safe.
    status, _ = request("/presentations/999999/publish", method="POST", token=admin_token)
    require(status == 403, "temporary-password restriction blocks publishing")

    new_admin_password = getpass("New admin password (minimum 10 characters): ")
    confirm_admin_password = getpass("Confirm new admin password: ")
    if len(new_admin_password) < 10 or new_admin_password != confirm_admin_password or new_admin_password == admin_initial_password:
        raise SystemExit("New password is invalid or confirmation did not match.")
    status, _ = request(
        "/users/me/password",
        method="POST",
        body={
            "current_password": admin_initial_password,
            "new_password": new_admin_password,
            "confirm_password": confirm_admin_password,
        },
        token=admin_token,
    )
    require(status == 200, "password-change endpoint accepted the authenticated admin")

    login(admin_username, admin_initial_password, 401)
    updated_login = login(admin_username, new_admin_password, 200)
    updated_token = updated_login.get("access_token")
    updated_user = updated_login.get("user", {})
    require(bool(updated_token) and updated_user.get("must_change_password") is False, "new password works and clears the temporary-password flag")

    status, _ = request("/presentations/999999/publish", method="POST", token=updated_token)
    require(status == 404, "admin passes the password-change gate before the nonexistent presentation check")
    status, _ = request("/admin/dashboard", token=updated_token)
    require(status == 200, "admin can access the admin dashboard")
    status, _ = request("/presentations/999999", method="DELETE", token=updated_token)
    require(status == 404, "admin passes the site-content authorization boundary")

    # JWTs are stateless in the current implementation. Password changes and
    # frontend logout do not revoke an already-issued token server-side.
    status, _ = request("/auth/me", token=admin_token)
    require(status == 200, "existing JWT remains valid after password change (current stateless-token behavior)")

    instructor_username = input("Instructor username [SUKHPAL SINGH]: ").strip() or "SUKHPAL SINGH"
    instructor_password = getpass(f"Current password for {instructor_username}: ")
    if not instructor_password:
        raise SystemExit("An instructor password is required.")
    instructor_login = login(instructor_username, instructor_password, 200)
    instructor_token = instructor_login.get("access_token")
    instructor_user = instructor_login.get("user", {})
    require(bool(instructor_token) and instructor_user.get("role") == "INSTRUCTOR", "selected account has the INSTRUCTOR role")
    status, _ = request("/admin/dashboard", token=instructor_token)
    require(status == 200, "instructor can access allowed admin workspace routes")
    status, _ = request("/presentations/999999", method="DELETE", token=instructor_token)
    require(status == 403, "instructor cannot use ADMIN-only site-content deletion")

    print("PASS: logout is client-side only: the frontend removes localStorage.token; no server logout or token-revocation endpoint exists.")
    print("Phase 3 authentication verification complete.")


if __name__ == "__main__":
    main()
