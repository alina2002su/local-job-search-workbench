# Local Job Search Workbench Agent Skill

A portable Agent Skill for building a private localhost job-search workbench with a Chrome JD Clipper, local JD and resume libraries, application tracking, To-do and interview linkage, and optional read-only Feishu Base import.

The package follows the Agent Skills directory structure. The same core files are used across supported agents; only the loading method changes.

## Install

Download or clone this complete directory. Do not copy only `SKILL.md`.

- **Codex:** place the directory in your Codex skills location or use its supported repository/package installation flow.
- **Claude Code:** place it at `~/.claude/skills/local-job-search-workbench/` for personal use or `.claude/skills/local-job-search-workbench/` inside one project.
- **WorkBuddy:** expose the same directory to the Claude Code installation used by WorkBuddy.
- **Doubao and prompt-only agents:** upload the directory files if supported, then paste the content of `adapters/prompt-only/START_HERE.md`. These environments can complete the local build only when they provide local file and command execution.

Ask the agent to “use local-job-search-workbench to build my private local job-search workbench.” The agent should collect local choices, preserve privacy boundaries, and verify what it actually performs.

## Privacy

This repository must contain no personal paths, credentials, Feishu identifiers, real job records, resumes, databases, browser data, or logs. Runtime configuration belongs only in each user's generated project.

See `references/platform-compatibility.md` for the support matrix and limitations.
