#!/usr/bin/env python3
"""Account-independent Sub2API deployment helper; Python 3.9+, standard library only."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
SECRETS = ("POSTGRES_PASSWORD", "REDIS_PASSWORD", "JWT_SECRET", "TOTP_ENCRYPTION_KEY", "ADMIN_PASSWORD")


def load_env():
    if not ENV_FILE.is_file():
        raise ValueError("Run init first.")
    values = {}
    for line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    for key in (*SECRETS, "ADMIN_EMAIL"):
        if not values.get(key) or "__GENERATE__" in values[key]:
            raise ValueError(f"Missing generated value: {key}")
    port = int(values["SERVER_PORT"])
    if not 1024 <= port <= 65535:
        raise ValueError("SERVER_PORT must be between 1024 and 65535.")
    ipaddress.IPv4Address(values["BIND_HOST"])
    return values


def initialize(args):
    if ENV_FILE.exists():
        load_env()
        print("Existing team/.env preserved; no password or settings were replaced.")
        return
    ipaddress.IPv4Address(args.bind_host)
    email = args.admin_email or f"admin-{secrets.token_hex(4)}@team-api.invalid"
    if "@" not in email or any(c in email for c in "\r\n\"' #="):
        raise ValueError("Invalid administrator email.")
    values = {key: secrets.token_hex(32) for key in SECRETS}
    values.update(ADMIN_EMAIL=email, BIND_HOST=args.bind_host, SERVER_PORT=str(args.port))
    lines = []
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        key = line.split("=", 1)[0]
        lines.append(f"{key}={values[key]}" if key in values else line)
    fd = os.open(ENV_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(lines) + "\n")
    load_env()
    print("Created team/.env with independent random credentials. This file stays local.")


def compose(*arguments):
    values = load_env()
    if not shutil.which("docker"):
        raise ValueError("Install Docker Engine/Desktop and Docker Compose first.")
    # The file, not ambient shell variables, defines this deployment.
    environment = os.environ.copy()
    environment.update(values)
    subprocess.run([
        "docker", "compose", "--env-file", str(ENV_FILE),
        "-f", str(ROOT / "compose.yaml"), *arguments,
    ], env=environment, check=True)


def api(path, method="GET", body=None, token=None):
    values = load_env()
    # Never send administrator credentials to a remote host supplied on a command line.
    address = values["BIND_HOST"]
    address = "127.0.0.1" if address == "0.0.0.0" else address
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"http://{address}:{values['SERVER_PORT']}{path}",
        data=None if body is None else json.dumps(body).encode(),
        headers=headers, method=method,
    )
    try:
        # Local deployment checks must not travel through a system HTTP proxy.
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=20) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 423:
            raise ValueError("First sign in to the web admin and complete its required acknowledgement; then rerun configure.") from None
        raise ValueError(f"{method} {path}: HTTP {error.code}") from None
    if isinstance(result, dict) and result.get("code", 0) not in (0, "0"):
        raise ValueError(f"{method} {path} returned an application error.")
    return result.get("data", result)


def login():
    values = load_env()
    result = api("/api/v1/auth/login", "POST", {
        "email": values["ADMIN_EMAIL"], "password": values["ADMIN_PASSWORD"],
    })
    token = result.get("access_token")
    if not token:
        raise ValueError("Login did not return an access token; finish interactive login in the browser.")
    return token


def configure():
    token = login()
    current = api("/api/v1/admin/settings", token=token)
    desired = {
        "site_name": "Team API", "registration_enabled": False,
        "promo_code_enabled": False, "invitation_code_enabled": False,
        "purchase_subscription_enabled": False, "payment_enabled": False,
        "default_concurrency": int(load_env()["DEFAULT_USER_CONCURRENCY"]),
    }
    # Preserve the complete settings representation; do not reset unrelated options.
    current.update(desired)
    api("/api/v1/admin/settings", "PUT", current, token)
    actual = api("/api/v1/admin/settings", token=token)
    for key, expected in desired.items():
        if key in actual and actual[key] != expected:
            raise ValueError(f"Setting did not persist: {key}")
    print("Team settings applied: registration/payments disabled; member count is unrestricted.")


def check():
    api("/health")
    print("PASS: health endpoint")
    profile = api("/api/v1/auth/me", token=login())
    if profile.get("role") != "admin":
        raise ValueError("The configured login is not an administrator.")
    print("PASS: administrator login and authenticated profile")
    if profile.get("run_mode") != "simple":
        raise ValueError("Expected the internal simple mode.")
    print("PASS: internal simple mode")
    print("Upstream model requests are not tested; no upstream account is bundled.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Generate local credentials once")
    init.add_argument("--admin-email")
    init.add_argument("--bind-host", default="127.0.0.1")
    init.add_argument("--port", type=int, choices=range(1024, 65536), default=8080, metavar="PORT")
    for action in ("validate", "start", "stop", "status", "logs", "check", "configure"):
        commands.add_parser(action)
    args = parser.parse_args()
    if args.command == "init":
        initialize(args)
    elif args.command == "validate":
        compose("config", "--quiet")
    elif args.command == "start":
        compose("config", "--quiet")
        compose("up", "-d", "--wait", "--wait-timeout", "240")
        print(f"Admin: http://127.0.0.1:{load_env()['SERVER_PORT']}; credentials: team/.env")
    elif args.command == "stop":
        compose("down")  # Named volumes intentionally survive routine stops.
    elif args.command == "status":
        compose("ps")
    elif args.command == "logs":
        compose("logs", "--tail", "100", "sub2api")
    elif args.command == "check":
        check()
    elif args.command == "configure":
        configure()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
