# Codex Automation

Project-local MCP servers and setup tooling for Codex automation.

## Fresh Mac Setup

```sh
git clone git@github.com:bxthomas/codex-automation.git
cd codex-automation
./bin/cx install
./bin/cx install --install-cx
./bin/cx doctor
```

`cx install` updates `~/.codex/config.toml` with the MCP servers listed in `codex-automation.json`. It makes a timestamped backup before editing.

`cx install --install-cx` symlinks `cx` into `~/.local/bin`.

`cx doctor` checks local command availability, Codex MCP config, and relevant environment variables.

## Commands

```sh
./bin/cx install              # install all MCP server config
./bin/cx install messages     # install one MCP server
./bin/cx install --install-cx # put cx on PATH as ~/.local/bin/cx
./bin/cx install --install-codex-wrapper
./bin/cx install --install-imessage-agent --allowed-handle tamikomadori@yahoo.com
./bin/cx doctor               # inspect local setup
./bin/cx imessage-agent-status
./bin/cx exec "prompt"        # run Codex with automation secrets loaded
```

`--install-codex-wrapper` installs `~/.local/bin/codex` as a wrapper that loads automation secrets through `cx exec` before launching the real Codex binary. Use this on Macs where direct `codex` starts without `HOME_ASSISTANT_TOKEN` in the shell environment. Keep `~/.local/bin` before the real Codex location in `PATH`.

The old `./bin/codex-automation` path remains as a compatibility wrapper for `./bin/cx`.

## Optional iMessage Trigger

One Mac can listen for trusted iMessage commands and invoke Codex. This is intentionally opt-in; a normal `cx install` does not install or start the listener.

```sh
./bin/cx install --install-imessage-agent --allowed-handle tamikomadori@yahoo.com
```

By default the listener:

- reads new inbound Messages rows every 5 seconds
- only accepts exact allowlisted handles
- only runs messages that start with `!codex `
- invokes `./bin/cx exec` in this repo
- sends a concise iMessage reply with Codex output
- stores its cursor in `~/Library/Application Support/codex-automation/imessage-codex-agent-state.json`
- installs a selectable app wrapper at `~/Applications/Codex iMessage Agent.app`
- runs as `~/Library/LaunchAgents/com.brianthomas.imessage-codex-agent.plist`

Useful options:

```sh
./bin/cx install --install-imessage-agent \
  --allowed-handle tamikomadori@yahoo.com \
  --prefix '!codex ' \
  --poll-seconds 10 \
  --reply-mode summary
```

The LaunchAgent uses `KeepAlive` and `ThrottleInterval` so launchd restarts it after a crash without tight restart loops.

Grant Full Disk Access to `~/Applications/Codex iMessage Agent.app`, otherwise macOS will block reads from `~/Library/Messages/chat.db`. The app wrapper exists because Full Disk Access often refuses hidden runtime binaries.

Check whether it is loaded and running:

```sh
./bin/cx imessage-agent-status
```

`./bin/cx doctor` also includes this status.

## MCP Servers

- `home-assistant`: Home Assistant HTTP MCP server at `http://192.168.40.142:8123/api/mcp`.
- `vestaboard`: Project-local stdio MCP server for concise Vestaboard sends.
- `messages`: Project-local stdio MCP server for macOS Messages send and local message lookup.

## Secrets

The Home Assistant token is read from AWS Secrets Manager secret `automation`, key `HOME_ASSISTANT_TOKEN`.

The Vestaboard Read/Write key is read from AWS Secrets Manager secret `automation`, key `VESTABOARD_RW_KEY`.

The LaunchAgent helper loads selected secrets into the user launchd environment with `launchctl setenv`. It does not write token files to disk.
