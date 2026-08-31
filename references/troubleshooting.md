# Troubleshooting

Read this only when installation, synchronization, clipping, or linkage fails.

| Symptom | Check | Recovery |
|---|---|---|
| Port already in use | Preflight `port_free`, stale PID, health endpoint | Reuse a healthy instance or choose another port and regenerate extension origin |
| Workbench will not start | Python version, dependency installation, server log | Fix environment, rerun start script; do not delete data |
| Extension reports offline | `/api/health`, manifest host permission, configured port | Start service, reload extension, retry |
| Extension path is wrong | Health response `save_directory` | Correct local config and restart; popup must not hard-code a path |
| JD content is incomplete | JSON-LD, selection, page container, text length | Select JD text or use raw-page fallback |
| Duplicate JD files | URL normalization, external ID, hash | Repair dedup logic; never remove versions blindly |
| Saved JD does not create an application | watcher, startup scan, imported file row, parser error | Run manual rescan and inspect clipping/server logs |
| Feishu sync fails | CLI discovery, auth status, Base/Table/View IDs, field names | Re-authenticate or fix identifiers; do not print tokens in reports |
| Local pool status reverts | `local_pool_status` and display precedence | Restore local precedence; remote sync must not update the local override |
| Deleted pool row returns | dismissal row and remote record ID | Recreate dismissal and rerun sync |
| Sorting arrow changes but rows do not | `sort/dir`, comparator, raw sort value, JS event | Fix both server and client sorting, then test observable order |
| Save/delete jumps to top | form preserve-scroll marker and pathname-scoped storage | Restore shared submit/restore behavior |
| To-do is missing | next action, DDL format, reconciliation | Correct data and run reconciliation |
| Deleted automatic task returns immediately | task type, source stage, dismissal | Persist stage-specific dismissal |
| Interview is absent | `next_action`, interview stage set, future DDL | Correct next action/time; do not infer from current stage |
| Existing user field is overwritten | `manual_fields` | Restore lock and source value from backup |

Back up the database before schema repair or data correction. Prefer narrow SQL updates with verified IDs; never reset or replace the entire database to fix one row.
