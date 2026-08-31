# 0→1 implementation workflow

Read this when creating a new workbench or repairing an incomplete installation.

## Target architecture

```text
Feishu Base (pre-application opportunities)
        │ manual read-only sync
        ▼
local job_pool cache ── open JD link ──> recruitment website
                                              │ explicit user click
                                              ▼
                                      Chrome JD Clipper
                                              │ localhost API
                                              ▼
local JD library ── scan/watch ──> applications ──> history / todos / interviews
                                              │
                                              ▼
                                            SQLite
```

The remote source supplies candidate jobs. The local workbench owns decisions, application progress, tasks, resume bindings, and history. Never write local progress back to Feishu unless a user separately requests a two-way integration.

## Build order

1. Run `scripts/preflight.py` for the chosen root, host, and port.
2. Resolve required choices: project root, product name, timezone, port, and whether Feishu is enabled.
3. Run `scripts/install_workbench.py`. Do not use `--install-deps` without permission when it would download packages.
4. If Feishu is enabled, obtain Base Token, Table ID, View ID, and an authenticated `lark-cli` path. Store identifiers only in the generated local config.
5. Run `scripts/verify_workbench.py` before starting.
6. Start the local service with the generated start script.
7. Run verification again with `--check-running`.
8. Ask the user to load the generated `browser-extension` directory from Chrome's extensions page. Browser UI actions remain user-controlled.
9. Perform an end-to-end test with synthetic data before touching personal JD or resume files.

## Core page behavior

- Dashboard: local KPIs, today's tasks, recent progress, and opportunity radar. Long progress lists scroll inside fixed-height cards.
- Job pool: search and filters, Feishu JD link, local decision status, detail view, and recoverability-aware delete semantics.
- Applications: editable city, current stage, next action, DDL, and resume binding. Sorting must reorder rows rather than only changing icons.
- To-do: always-visible manual form, automatic stage-driven tasks, circular two-way completion controls, and delete suppression for automatic tasks.
- Interviews: derive the displayed round from `next_action`, show future interviews, and use the 7-day flag only for dashboard counts.
- Resume library: scan only the configured local directory and bind by path; never upload by default.
- Settings: connection health, Feishu sync, JD rescan, database path, and backup action.

## Feishu setup

Expected fields:

```text
岗位名称、公司名称、业务线/部门、城市、岗位方向、职位ID、JD链接、
截止日期、来源、优先级、投递建议、岗位匹配点、风险点、长期壁垒、
长期壁垒说明、AI替代风险、岗位池状态、JD原文、备注
```

The `JD链接` parser must accept a native link object, Markdown link, or plain HTTP(S) text. Sync by remote record ID. Missing rows in one sync response do not authorize local deletion.

## Chrome JD Clipper

Use Manifest V3 with only:

- `activeTab`
- `scripting`
- `storage`
- the configured localhost origin

The popup shows the source URL, editable description, creation date, and save directory returned by `/api/health`. Capture priority is JSON-LD `JobPosting`, selected text, common JD containers, then page text. Saving equal content returns an existing result; changed content creates a versioned file.

## Application and task linkage

`current_status` means the stage already reached. `next_action` means the next event. Both are select fields backed by the same stage list. `next_event_at` is the occurrence time or deadline for the next action.

- Assessment or written test: one completion task due at the event time.
- Interview stage: preparation and attendance tasks; preparation defaults to 24 hours earlier.
- Offer with a time: one handling task.
- Terminal status: cancel unfinished automatic tasks, preserve manual tasks.

When a completed task is reopened, preserve its original DDL so it returns to the correct time group. Deleting an automatic task writes a stage-specific dismissal so reconciliation does not recreate it until the stage changes.

## Safe update behavior

Before modifying an existing workbench:

1. Inspect its config, schema, current process, and dirty files.
2. Back up the database and config.
3. Add schema columns with idempotent migrations.
4. Preserve JD files, resumes, database rows, and local status overrides.
5. Run tests in an isolated database.
6. Restart once, then smoke-test the actual local service.

Do not overwrite a non-empty target with the installer. Update an existing installation by patching only the required components.
