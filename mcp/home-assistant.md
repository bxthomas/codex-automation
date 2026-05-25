# Home Assistant MCP

Home Assistant exposes an MCP server at:

```text
http://192.168.40.142:8123/api/mcp
```

Codex is configured with:

```sh
codex mcp add home-assistant \
  --url http://192.168.40.142:8123/api/mcp \
  --bearer-token-env-var HOME_ASSISTANT_TOKEN
```

For non-interactive `codex exec`, the server is pre-approved in `~/.codex/config.toml`:

```toml
[mcp_servers.home-assistant]
default_tools_approval_mode = "approve"
url = "http://192.168.40.142:8123/api/mcp"
bearer_token_env_var = "HOME_ASSISTANT_TOKEN"
```

The long-lived access token is stored in AWS Secrets Manager secret `automation` under key `HOME_ASSISTANT_TOKEN`.

The preferred setup is to load this once at macOS login:

```sh
cp com.brianthomas.codex-automation-env.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.brianthomas.codex-automation-env.plist
launchctl kickstart -k gui/$(id -u)/com.brianthomas.codex-automation-env
```

The LaunchAgent runs `bin/load-automation-env`, reads the token from AWS Secrets Manager, and loads it into the macOS user launchd environment with `launchctl setenv`. It does not write the token to disk.

Apps and processes launched from that user launchd session can inherit `HOME_ASSISTANT_TOKEN`. Terminal shells may need a new login session before they see the value. For shell-only use without launchd environment setup, use the project launcher below.

The project launcher remains available if you want an explicit per-command fallback:

```sh
./bin/cx exec "Turn on the living room lights."
```

The launcher does not print the token. It reads the `automation` secret, exports `HOME_ASSISTANT_TOKEN` for the child Codex process, and then replaces itself with `codex`.

If direct `codex` from a shell starts without `HOME_ASSISTANT_TOKEN`, install the wrapper:

```sh
./bin/cx install --install-codex-wrapper
```

This writes `~/.local/bin/codex`, which loads automation secrets through `cx exec` before launching the real Codex binary.
