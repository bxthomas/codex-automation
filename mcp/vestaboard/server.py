#!/usr/bin/env python3
"""Small stdio MCP server for sending concise messages to a Vestaboard."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any


BOARD_WIDTH = 22
BOARD_HEIGHT = 6
BOARD_CHARS = BOARD_WIDTH * BOARD_HEIGHT
ALLOWED = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?'-:/()\"")
VESTABOARD_URL = "https://rw.vestaboard.com"
AWS_SECRET_NAME = "automation"
AWS_SECRET_KEY = "VESTABOARD_RW_KEY"
_VESTABOARD_RW_KEY: str | None = None


def sanitize(text: str) -> str:
    text = text.upper()
    filtered = "".join(ch if ch in ALLOWED else " " for ch in text)
    return re.sub(r"\s+", " ", filtered).strip()[:BOARD_CHARS]


def wrap_for_board(text: str) -> str:
    words = sanitize(text).split()
    lines: list[str] = []
    current = ""

    for word in words:
        while len(word) > BOARD_WIDTH:
            if current:
                lines.append(current)
                current = ""
            lines.append(word[:BOARD_WIDTH])
            word = word[BOARD_WIDTH:]

        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= BOARD_WIDTH:
            current = candidate
        else:
            lines.append(current)
            current = word

        if len(lines) == BOARD_HEIGHT:
            break

    if current and len(lines) < BOARD_HEIGHT:
        lines.append(current)

    return "\n".join(lines)[:BOARD_CHARS]


def read_vestaboard_key_from_aws() -> str:
    command = [
        "aws",
        "secretsmanager",
        "get-secret-value",
        "--secret-id",
        AWS_SECRET_NAME,
        "--query",
        "SecretString",
        "--output",
        "text",
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("aws CLI not found; cannot read Vestaboard key from Secrets Manager.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Timed out reading Vestaboard key from AWS Secrets Manager.") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        message = "Failed to read AWS Secrets Manager secret 'automation'."
        if detail:
            message = f"{message} AWS CLI said: {detail}"
        raise RuntimeError(message) from exc

    secret = completed.stdout.strip()
    if not secret:
        raise RuntimeError("AWS Secrets Manager secret 'automation' returned an empty SecretString.")

    try:
        parsed = json.loads(secret)
    except json.JSONDecodeError:
        return secret

    if not isinstance(parsed, dict):
        raise RuntimeError("AWS Secrets Manager secret 'automation' must be a JSON object or raw key string.")

    key = parsed.get(AWS_SECRET_KEY)
    if not isinstance(key, str) or not key.strip():
        raise RuntimeError("AWS Secrets Manager secret 'automation' does not contain VESTABOARD_RW_KEY.")
    return key.strip()


def get_vestaboard_key() -> str:
    global _VESTABOARD_RW_KEY
    if _VESTABOARD_RW_KEY:
        return _VESTABOARD_RW_KEY

    key = os.getenv(AWS_SECRET_KEY)
    if key:
        _VESTABOARD_RW_KEY = key
        return key

    _VESTABOARD_RW_KEY = read_vestaboard_key_from_aws()
    return _VESTABOARD_RW_KEY


def post_vestaboard(message: str) -> dict[str, Any]:
    key = get_vestaboard_key()

    payload = json.dumps({"text": message[:BOARD_CHARS].upper()}).encode("utf-8")
    request = urllib.request.Request(
        VESTABOARD_URL,
        data=payload,
        headers={
            "X-Vestaboard-Read-Write-Key": key,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8", errors="replace")
            return {"status": response.status, "body": body}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Vestaboard API returned HTTP {exc.code}: {body}") from exc


def content_text(text: str) -> list[dict[str, str]]:
    return [{"type": "text", "text": text}]


TOOLS: list[dict[str, Any]] = [
    {
        "name": "send_vestaboard_text",
        "description": (
            "Send a concise text message to the user's Vestaboard. "
            "The server uppercases, sanitizes, wraps to 6 rows x 22 columns, and truncates to 132 characters."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Message to display. Keep it brief and useful.",
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "When true, format the message but do not send it.",
                    "default": False,
                },
            },
            "required": ["message"],
            "additionalProperties": False,
        },
    },
]


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    dry_run = bool(arguments.get("dry_run", False))

    if name == "send_vestaboard_text":
        message = wrap_for_board(str(arguments["message"]))
    else:
        raise RuntimeError(f"Unknown tool: {name}")

    result: dict[str, Any] = {"message": message, "character_count": len(message)}
    if dry_run:
        result["sent"] = False
    else:
        result["vestaboard"] = post_vestaboard(message)
        result["sent"] = True

    return {
        "content": content_text(json.dumps(result, indent=2)),
        "structuredContent": result,
    }


def handle(request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    request_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "vestaboard", "version": "0.1.0"},
            },
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}

    if method == "tools/call":
        params = request.get("params") or {}
        try:
            result = call_tool(params["name"], params.get("arguments") or {})
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": str(exc)},
            }

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            response = handle(request)
        except Exception as exc:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": str(exc)},
            }
        if response is not None:
            sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
