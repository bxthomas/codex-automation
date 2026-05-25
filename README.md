# Codex Automation

Project-local MCP servers and setup tooling for Codex automation.

## Fresh Mac Setup

```sh
git clone git@github.com:bxthomas/codex-automation.git
cd codex-automation
./bin/cx install
./bin/cx doctor
```

`cx install` updates `~/.codex/config.toml` with the MCP servers listed in `codex-automation.json`. It makes a timestamped backup before editing.

`cx doctor` checks local command availability, Codex MCP config, and relevant environment variables.

## Commands

```sh
./bin/cx install              # install all MCP server config
./bin/cx install messages     # install one MCP server
./bin/cx doctor               # inspect local setup
./bin/cx exec "prompt"        # run Codex with automation secrets loaded
```

The old `./bin/codex-automation` path remains as a compatibility wrapper for `./bin/cx`.

## MCP Servers

- `home-assistant`: Home Assistant HTTP MCP server at `http://192.168.40.142:8123/api/mcp`.
- `vestaboard`: Project-local stdio MCP server for concise Vestaboard sends.
- `messages`: Project-local stdio MCP server for macOS Messages send and local message lookup.

## Secrets

The Home Assistant token is read from AWS Secrets Manager secret `automation`, key `HOME_ASSISTANT_TOKEN`.

The Vestaboard Read/Write key is read from AWS Secrets Manager secret `automation`, key `VESTABOARD_RW_KEY`.

The LaunchAgent helper loads selected secrets into the user launchd environment with `launchctl setenv`. It does not write token files to disk.
