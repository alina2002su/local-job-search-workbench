# Data and state contract

Read this before changing the database, Feishu mapping, import logic, or stage/task behavior.

## Ownership

| Data | Owner | Rule |
|---|---|---|
| Candidate job evaluation fields | Feishu Base | Read into local cache by remote record ID |
| Local job-pool decision | SQLite | Local override survives remote sync |
| JD source, capture time, description, content | Local Markdown | Version instead of overwrite |
| Application progress and next action | SQLite | Human edits are authoritative |
| History, tasks, dismissals | SQLite | Transactional local state |
| Resumes | Configured local directory | Read-only scan and path binding |

## Tables

- `job_pool`: remote cache, link, evaluation fields, `local_pool_status`, optional linked application.
- `job_pool_dismissals`: remote record IDs hidden after local deletion.
- `applications`: parsed JD snapshot, manual fields, current stage, next action, DDL, resume binding.
- `status_history`: append on actual current-stage changes.
- `todos`: manual or automatic tasks, DDL, completion time, source stage.
- `todo_dismissals`: stage-specific suppression for deleted automatic tasks.
- `imported_files`: file identity, hash, mtime, and linked application.
- `settings`: local operational state such as last sync time.

Use foreign keys, WAL, transactions for multi-table actions, and an idempotent startup migration for new columns.

## Job-pool status invariant

Selectable values:

```text
待投递、已投递、不合适
```

Effective display order:

```text
valid local_pool_status
  > linked application means 已投递
  > recognized remote pool status
  > default 待投递
```

Map legacy `待评估` to `待投递` and remote `已决定不投` to `不合适`. Selecting `已投递` in the job pool does not create an application. Only JD import creates or links an application.

## Application stages

```text
已投递、测评、笔试、群面、一面、二面、三面、终面、HR面、
Offer、人才库、未通过、主动放弃
```

Use the same list for current stage and next action. Interview stages are `群面、一面、二面、三面、终面、HR面`. Terminal states cancel only automatic pending tasks.

## JD metadata

```yaml
company: parsed company
position: parsed position
business: parsed team or function
city: [parsed cities]
job_id: external job identifier
source_url: source page
captured_at: ISO 8601 timestamp
capture_source: browser_extension
description: user-authored note
content_hash: normalized body hash
```

Deduplicate by normalized URL, external ID, company+position, then content hash. Preserve earlier versions.

## Manual field protection

Automatic parsing may fill empty values. After a user saves company, position, business, or city, add the field to `manual_fields`. Later scans can refresh JD source fields but cannot overwrite locked business fields.

## Sorting contract

- Text: locale-aware company/position/city comparison.
- Dates: ISO timestamp order; empty values last.
- Urgency: overdue, urgent, high, normal, relaxed, missing.
- Stage: configured recruitment sequence.
- Resume: normalized filename.

Server-side `sort` and `dir` are authoritative. Client-side sorting may improve responsiveness but must use stable raw values and match server semantics.
