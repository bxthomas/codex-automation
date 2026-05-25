# Codex Project Instructions

The user has a Vestaboard MCP server available for this project.

When the user asks to send something to the Vestaboard:

- Use the `vestaboard` MCP tools instead of writing a one-off script.
- Call `send_vestaboard_text` with the final message to display.
- Keep Vestaboard copy concise: 6 rows, 22 columns, 132 total characters.
- Do not expect the MCP server to fetch weather, news, or any other outside content. Codex should gather the content using its normal tools, summarize it into Vestaboard-sized copy, then send it with `send_vestaboard_text`.
- For weather requests, look up the forecast first. If the user's location is ambiguous or unavailable from context, ask for the location before sending.

Home Assistant is available as an HTTP MCP server named `home-assistant` at `http://192.168.40.142:8123/api/mcp`.

When using `codex exec` from a shell and Home Assistant tools are needed, prefer `./bin/cx exec ...`; it loads `HOME_ASSISTANT_TOKEN` from AWS Secrets Manager secret `automation` before starting Codex.
