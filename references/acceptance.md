# Acceptance checklist

Read this during final verification or before packaging the generated workbench.

## Installation

- Project paths come from user parameters; no template author paths or credentials remain.
- Re-running the installer refuses to overwrite a non-empty target.
- Start/stop are repeatable and do not create duplicate services.
- `/health` and `/api/health` work on localhost.
- Startup initializes/migrates and backs up the database.

## Feishu and job pool

- Repeat sync does not duplicate rows or delete locally cached rows.
- JD links open the exact remote field URL.
- Status dropdown contains only `待投递、已投递、不合适`.
- Legacy waiting status displays as `待投递`.
- Local status survives sync; selecting `已投递` does not create an application.
- Deleted rows remain dismissed on later sync.

## Clipper and JD import

- Popup shows editable description, source, creation date, and actual configured save directory.
- Equal content is not duplicated; changed content creates a new version.
- Data is sent only to the configured localhost origin.
- Imported JD creates one application and can link the matching pool record.
- Human-confirmed business fields survive rescans.

## Applications, tasks, and interviews

- Current stage and next action share the configured select list.
- Table headers cause real ascending/descending row changes.
- Stage changes append history and reconcile automatic tasks.
- Manual task form is always visible and successful creation persists.
- Completion can be reversed without losing DDL.
- Deletion is rounded, intentional, and does not expose an underlying red edge.
- Future interview next actions show company, role, round, and time; no fake progress bar appears.
- Mutating actions keep the current page and scroll position.

## Privacy

- No real JD, resume, database, remote token, user name, home path, or browser data is packaged.
- Generated config and reports redact credentials.
- The default service listens only on `127.0.0.1`.
