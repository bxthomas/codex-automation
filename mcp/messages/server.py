#!/usr/bin/env python3
"""Project-local MCP server for macOS Messages."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any


CHAT_DB = Path.home() / "Library" / "Messages" / "chat.db"
MAX_LIMIT = 100


def content_text(text: str) -> list[dict[str, str]]:
    return [{"type": "text", "text": text}]


def clamp_limit(value: Any, default: int = 20) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError):
        limit = default
    return max(1, min(limit, MAX_LIMIT))


def send_message(recipient: str, message: str, service: str, dry_run: bool) -> dict[str, Any]:
    if not recipient.strip():
        raise RuntimeError("recipient is required.")
    if not message.strip():
        raise RuntimeError("message is required.")

    normalized_service = service.strip().lower() or "imessage"
    if normalized_service not in {"imessage", "sms"}:
        raise RuntimeError("service must be 'iMessage' or 'SMS'.")

    result = {
        "recipient": recipient,
        "message": message,
        "service": "SMS" if normalized_service == "sms" else "iMessage",
        "sent": False,
    }
    if dry_run:
        return result

    script = r'''
on run argv
  set targetRecipient to item 1 of argv
  set bodyText to item 2 of argv
  set serviceKind to item 3 of argv

  tell application "Messages"
    if serviceKind is "sms" then
      set targetService to 1st service whose service type = SMS
    else
      set targetService to 1st service whose service type = iMessage
    end if
    set targetBuddy to buddy targetRecipient of targetService
    send bodyText to targetBuddy
  end tell
end run
'''
    completed = subprocess.run(
        ["osascript", "-", recipient, message, normalized_service],
        input=script,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"Messages send failed: {detail or 'osascript exited non-zero'}")

    result["sent"] = True
    return result


def connect_messages_db() -> sqlite3.Connection:
    if not CHAT_DB.exists():
        raise RuntimeError(f"Messages database not found at {CHAT_DB}.")
    uri = f"file:{CHAT_DB}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
    except sqlite3.OperationalError as exc:
        raise RuntimeError(
            "Could not open Messages database. Grant Full Disk Access to the app or shell running Codex."
        ) from exc
    connection.row_factory = sqlite3.Row
    return connection


def message_date_expr() -> str:
    return """
    CASE
      WHEN m.date > 1000000000000
      THEN datetime((m.date / 1000000000) + strftime('%s','2001-01-01'), 'unixepoch', 'localtime')
      ELSE datetime(m.date + strftime('%s','2001-01-01'), 'unixepoch', 'localtime')
    END
    """


def list_recent_messages(limit: int, contact: str | None) -> list[dict[str, Any]]:
    query = f"""
        SELECT
          m.ROWID AS message_id,
          {message_date_expr()} AS date,
          h.id AS handle,
          c.display_name AS conversation,
          m.is_from_me AS is_from_me,
          m.text AS text
        FROM message m
        LEFT JOIN handle h ON h.ROWID = m.handle_id
        LEFT JOIN chat_message_join cmj ON cmj.message_id = m.ROWID
        LEFT JOIN chat c ON c.ROWID = cmj.chat_id
        WHERE m.text IS NOT NULL
    """
    params: list[Any] = []
    if contact:
        query += " AND (h.id LIKE ? OR c.display_name LIKE ?)"
        like = f"%{contact}%"
        params.extend([like, like])
    query += " ORDER BY m.date DESC LIMIT ?"
    params.append(limit)

    with connect_messages_db() as connection:
        rows = connection.execute(query, params).fetchall()

    messages: list[dict[str, Any]] = []
    for row in rows:
        messages.append(
            {
                "message_id": row["message_id"],
                "date": row["date"],
                "handle": row["handle"],
                "conversation": row["conversation"],
                "direction": "sent" if row["is_from_me"] else "received",
                "text": row["text"],
            }
        )
    return messages


def list_conversations(limit: int, query_text: str | None) -> list[dict[str, Any]]:
    query = """
        SELECT
          c.ROWID AS conversation_id,
          c.display_name AS display_name,
          c.chat_identifier AS chat_identifier,
          MAX(m.date) AS last_date_raw,
          COUNT(m.ROWID) AS message_count
        FROM chat c
        LEFT JOIN chat_message_join cmj ON cmj.chat_id = c.ROWID
        LEFT JOIN message m ON m.ROWID = cmj.message_id
    """
    params: list[Any] = []
    if query_text:
        query += " WHERE c.display_name LIKE ? OR c.chat_identifier LIKE ?"
        like = f"%{query_text}%"
        params.extend([like, like])
    query += " GROUP BY c.ROWID ORDER BY last_date_raw DESC LIMIT ?"
    params.append(limit)

    with connect_messages_db() as connection:
        rows = connection.execute(query, params).fetchall()

    return [
        {
            "conversation_id": row["conversation_id"],
            "display_name": row["display_name"],
            "chat_identifier": row["chat_identifier"],
            "message_count": row["message_count"],
        }
        for row in rows
    ]


TOOLS: list[dict[str, Any]] = [
    {
        "name": "send_text_message",
        "description": "Send a text through macOS Messages using iMessage or SMS.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "recipient": {
                    "type": "string",
                    "description": "Phone number, email address, or Messages handle.",
                },
                "message": {"type": "string", "description": "Message body to send."},
                "service": {
                    "type": "string",
                    "enum": ["iMessage", "SMS"],
                    "default": "iMessage",
                    "description": "Messages service to use.",
                },
                "dry_run": {
                    "type": "boolean",
                    "default": False,
                    "description": "When true, validate and return payload without sending.",
                },
            },
            "required": ["recipient", "message"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_recent_messages",
        "description": "List recent macOS Messages rows visible in the local Messages database.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": MAX_LIMIT,
                },
                "contact": {
                    "type": "string",
                    "description": "Optional phone/email/name filter.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "list_conversations",
        "description": "List recent Messages conversations from the local Messages database.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": MAX_LIMIT,
                },
                "query": {
                    "type": "string",
                    "description": "Optional conversation name or identifier filter.",
                },
            },
            "additionalProperties": False,
        },
    },
]


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "send_text_message":
        result = send_message(
            str(arguments["recipient"]),
            str(arguments["message"]),
            str(arguments.get("service", "iMessage")),
            bool(arguments.get("dry_run", False)),
        )
    elif name == "list_recent_messages":
        result = {
            "messages": list_recent_messages(
                clamp_limit(arguments.get("limit")),
                arguments.get("contact"),
            )
        }
    elif name == "list_conversations":
        result = {
            "conversations": list_conversations(
                clamp_limit(arguments.get("limit")),
                arguments.get("query"),
            )
        }
    else:
        raise RuntimeError(f"Unknown tool: {name}")

    return {
        "content": content_text(json.dumps(result, indent=2, ensure_ascii=False)),
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
                "serverInfo": {"name": "messages", "version": "0.1.0"},
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
            sys.stdout.write(json.dumps(response, separators=(",", ":"), ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
