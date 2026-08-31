# Platform compatibility

The canonical source is the skill root: `SKILL.md`, `scripts/`, `references/`, and `assets/`. Keep product rules there. Platform adapters must not fork or rewrite the core workflow.

## Capability levels

| Environment | Load method | Full local build | Notes |
| --- | --- | --- | --- |
| Agent Skills compatible tools | Install or expose the whole skill directory | Yes, if file and command tools are available | Use the root `SKILL.md`. |
| Codex | Copy the whole directory into the user's Codex skills directory, or install it from a supported repository/package flow | Yes | `agents/openai.yaml` is optional Codex UI metadata; it is not part of the core workflow. |
| Claude Code | Copy the whole directory to `~/.claude/skills/local-job-search-workbench/` or `.claude/skills/local-job-search-workbench/` | Yes | Claude Code natively follows the Agent Skills standard. |
| WorkBuddy | Make the skill available to the underlying Claude Code installation | Yes, subject to WorkBuddy/Claude permissions | WorkBuddy is built on Claude Code; do not maintain a separate WorkBuddy-only workflow. |
| Doubao or another chat agent without a filesystem skill loader | Upload the package files when supported and paste `adapters/prompt-only/START_HERE.md` | Usually guided mode only | The agent must not claim it ran local scripts unless it actually has local file and command tools. |

## Portability rules

- Treat unknown frontmatter fields as optional metadata. The required portable fields are `name` and `description`.
- Do not use vendor-specific prompt substitutions, command injection syntax, tool names, or absolute installation paths in the canonical `SKILL.md`.
- Resolve resource paths relative to the directory containing `SKILL.md`.
- Keep secrets and personal data outside the skill. Receive them at runtime and store them only in the user's generated project configuration.
- If an agent cannot execute Python, it may explain or adapt the workflow but must not report verification as passed.
- If a platform adds a native adapter later, add only loading metadata or instructions. Keep business rules in the canonical files.

## Distribution layout

Publish the entire `local-job-search-workbench/` directory. A ZIP download or Git repository is acceptable. Do not publish only `SKILL.md`, because the installer, verification scripts, references, and sanitized project template are required.
