# Messages MCP Server

This project-local MCP server lets Codex interact with macOS Messages.

It exposes:

- `send_text_message`: sends a message through the Messages app with AppleScript.
- `list_recent_messages`: reads recent message rows from `~/Library/Messages/chat.db`.
- `list_conversations`: lists recent local Messages conversations.

## Permissions

macOS will enforce privacy permissions:

- Sending requires Automation permission for the process running Codex to control Messages.
- Reading requires Full Disk Access for the process running Codex, because Messages stores data in `~/Library/Messages/chat.db`.

The server does not store message data or credentials.

## Install

From this repo:

```sh
./bin/cx install messages
```

The full install command installs all configured MCP servers:

```sh
./bin/cx install
```

The generated Codex config entry is:

```toml
[mcp_servers.messages]
command = "python3"
args = ["/Users/brianthomas/codex-exec-test/mcp/messages/server.py"]

[mcp_servers.messages.tools.send_text_message]
approval_mode = "approve"
```
