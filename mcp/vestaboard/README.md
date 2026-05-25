# Vestaboard MCP Server

This project-local MCP server exposes one tool to Codex:

- `send_vestaboard_text`: formats and sends arbitrary text to the Vestaboard.

The server uses the same Read/Write API pattern as `/Users/brianthomas/frametv/aithemen.py`.
It deliberately does not fetch weather or other content. Codex should gather or reason about the content first, write a concise Vestaboard-sized message, then use this MCP tool only to send that text.

## Secret Lookup

For live sends, the server reads `VESTABOARD_RW_KEY` from AWS Secrets Manager secret `automation`.

The secret can either be a raw Read/Write key string or a JSON object containing:

```json
{
  "VESTABOARD_RW_KEY": "..."
}
```

For local testing, an environment variable named `VESTABOARD_RW_KEY` still takes precedence.

## Register With Codex

From this repo, register the server once with the repo installer:

```sh
./bin/cx install vestaboard
```

For non-interactive `codex exec`, the Vestaboard tool must be pre-approved because it has an external side effect. The working config in `~/.codex/config.toml` is:

```toml
[mcp_servers.vestaboard]
command = "python3"
args = ["/Users/brianthomas/codex-exec-test/mcp/vestaboard/server.py"]
default_tools_approval_mode = "approve"

[mcp_servers.vestaboard.tools.send_vestaboard_text]
approval_mode = "approve"
```

Then you can run:

```sh
codex exec "Please send the weather forecast to my vestaboard."
```
