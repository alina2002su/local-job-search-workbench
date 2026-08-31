---
name: local-job-search-workbench
description: Build, configure, verify, or repair a private localhost job-search workbench with a Chrome JD Clipper, optional read-only Feishu Base job-pool sync, local JD and resume libraries, application tracking, To-do automation, and interview linkage. Use in any file-and-terminal-capable agent when a user wants a reusable local recruiting or job-application dashboard; use planning mode when the agent cannot access local files or run commands.
metadata:
  compatibility: "Agent Skills compatible; full execution requires local file access, Python 3.9+, and permission to run commands"
---

# Local Job Search Workbench

Create a user-owned local workbench from the bundled sanitized template. Keep recruitment documents, resumes, progress, tasks, and the database on the user's machine by default.

## Establish the execution mode

Resolve the directory containing this `SKILL.md` as `skill_root`. Do not assume a Codex-, Claude-, WorkBuddy-, or operating-system-specific installation path.

Before changing anything, determine whether the current agent can:

1. read and write local files;
2. run Python and shell commands;
3. access a localhost service;
4. guide or control a browser;
5. access Feishu only after the user authorizes it.

Use **full execution mode** only when the first two capabilities are available. Otherwise use **guided mode**: collect the user's choices, produce exact files or instructions, and clearly identify the steps the user must run elsewhere. Never claim that a service, extension, or integration was installed when the current environment could not verify it.

## Non-negotiable privacy rules

- Never copy data, paths, credentials, identifiers, JD files, resumes, databases, logs, or branding from another user's installation.
- Derive every absolute path from the current user's chosen `project_root` at installation time.
- Do not embed Feishu tokens, Base/Table/View IDs, home-directory names, or browser data in this skill, generated source code, tests, or reports.
- Listen on `127.0.0.1` unless the user explicitly requests and understands a broader network exposure.
- Ask immediately before downloading dependencies, authenticating an external service, opening a GUI, or changing an existing live installation when authorization is required.

## Choose the mode

- **New build:** use the bundled template and installer.
- **Existing workbench repair/customization:** inspect the current config, schema, service, and user changes; back up first and patch only the necessary files. Do not run the new-build installer over a non-empty directory.
- **Planning or Skill review only:** read the relevant references and produce a design or gap report without mutating files.

For the complete build sequence, read [references/workflow.md](references/workflow.md). Before changing schema, statuses, sorting, JD import, or task linkage, read [references/data-contract.md](references/data-contract.md). Read [references/troubleshooting.md](references/troubleshooting.md) only for failures, and [references/acceptance.md](references/acceptance.md) for final verification.

## New-build workflow

1. Resolve or reasonably default: project root, product name, timezone, host, port, and whether Feishu sync is wanted. Default root is `~/LocalJobWorkbench`; default host is localhost.
2. Run `<skill_root>/scripts/preflight.py` with the selected root and port. Stop if the target is non-empty or the environment cannot safely create it.
3. Run `<skill_root>/scripts/install_workbench.py` without `--install-deps` unless dependency installation is authorized. Pass Feishu identifiers only when the user supplied them.
4. Run `<skill_root>/scripts/verify_workbench.py --project-root <path>`.
5. With authorization, install dependencies/start the generated service. Then rerun verification with `--check-running`.
6. Tell the user the generated Chrome extension directory and guide them through `chrome://extensions` → Developer mode → Load unpacked. Do not claim it is installed until Chrome shows it loaded.
7. If Feishu is enabled, validate user authentication and the configured Base/Table/View before syncing. Treat the flow as remote-read/local-manage.
8. Run an end-to-end check with synthetic data, then report actual locations and any remaining user action.

## Preserve these product invariants

- Job-pool local status options are `待投递、已投递、不合适`. A legacy waiting value displays as `待投递`.
- A local status override survives Feishu sync. Selecting `已投递` in the pool does not create an application.
- Only JD import creates or links an application; duplicate JD content does not create duplicates and changed content is versioned.
- `current_status` and `next_action` use the same stage choices; the next action plus DDL drives To-do and interview views.
- Manual fields override later automatic parsing.
- Reopening a completed task preserves its DDL; deleting an automatic task suppresses regeneration until the source stage changes.
- Sorting must change observable row order. Mutating actions preserve the current page and scroll position.
- Remote omission does not authorize local deletion. Local deletes use dismissal records so sync cannot silently restore them.

## Finish with evidence

Use the acceptance reference. Report the workbench URL, project root, extension directory, JD directory, resume directory, database, latest backup, logs, Feishu status, test results, and remaining manual steps. Redact credentials and do not include private document contents.

For installation and behavior differences across agents, read [references/platform-compatibility.md](references/platform-compatibility.md). This file changes loading instructions, not the workbench's product logic.
