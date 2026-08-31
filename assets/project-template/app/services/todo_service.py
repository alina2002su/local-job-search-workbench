from __future__ import annotations
from datetime import datetime, timedelta

INTERVIEWS = {"群面","一面","二面","三面","终面","HR面"}
TERMINAL = {"Offer","未通过","主动放弃"}

def _add(db, app_id, title, task_type, stage, due):
    if db.one("SELECT 1 FROM todo_dismissals WHERE application_id=? AND task_type=? AND source_stage=?", (app_id,task_type,stage)):
        return None
    now=db.now(); due_value = due.isoformat(timespec="seconds") if hasattr(due,"isoformat") else due
    return db.execute("INSERT INTO todos(application_id,title,task_type,source_stage,due_at,status,auto_generated,created_at,updated_at) VALUES(?,?,?,?,?,'pending',1,?,?)", (app_id,title,task_type,stage,due_value,now,now))

def add_todo(db, title: str, application_id=None, due_at=None):
    title=(title or "").strip()
    if not title:
        raise ValueError("请输入任务名称")
    if application_id is not None and not db.one("SELECT id FROM applications WHERE id=?",(application_id,)):
        raise ValueError("关联岗位不存在")
    now=db.now()
    return db.execute("INSERT INTO todos(application_id,title,task_type,due_at,status,auto_generated,created_at,updated_at) VALUES(?,?,'manual',?,'pending',0,?,?)",(application_id,title,due_at or None,now,now))

def delete_todo(db, todo_id: int):
    """删除待办；自动待办在当前招聘阶段内保持已忽略。"""
    todo=db.one("SELECT * FROM todos WHERE id=?",(todo_id,))
    if not todo:
        raise KeyError(todo_id)
    if todo["auto_generated"] and todo["application_id"]:
        db.execute("INSERT OR IGNORE INTO todo_dismissals(application_id,task_type,source_stage,created_at) VALUES(?,?,?,?)",
                   (todo["application_id"],todo["task_type"],todo["source_stage"] or "",db.now()))
    db.execute("DELETE FROM todos WHERE id=?",(todo_id,))

def toggle_todo(db, todo_id: int):
    """在待办与已完成之间切换，并保留原截止时间用于恢复分组。"""
    todo=db.one("SELECT status FROM todos WHERE id=?",(todo_id,))
    if not todo:
        raise KeyError(todo_id)
    now=db.now()
    if todo["status"] == "completed":
        db.execute("UPDATE todos SET status='pending',completed_at=NULL,updated_at=? WHERE id=?",(now,todo_id))
        return "pending"
    db.execute("UPDATE todos SET status='completed',completed_at=?,updated_at=? WHERE id=?",(now,now,todo_id))
    return "completed"

def sync_auto_todos(db, app):
    stage, app_id = app.get("next_action") or app["current_status"], app["id"]
    now=db.now()
    label=f'{app["company"]} {app["position"]}'.strip()
    due=app.get("next_event_at")
    desired=[]
    if stage in {"测评","笔试"}: desired.append((f'完成「{label}」{stage}',stage,stage,due))
    elif stage in INTERVIEWS:
        event=None
        if due:
            try: event=datetime.fromisoformat(due)
            except ValueError: pass
        prep_due=(event-timedelta(hours=24)) if event else None
        desired.append((f'准备 {label} {stage}',"prepare",stage,prep_due))
        desired.append((f'参加 {label} {stage}',"attend",stage,event))
    elif stage=="Offer" and due: desired.append((f'处理 {label} Offer',"offer",stage,due))
    pending=db.all("SELECT * FROM todos WHERE application_id=? AND auto_generated=1 AND status='pending' ORDER BY id",(app_id,))
    used=set()
    for title,task_type,source_stage,target_due in desired:
        due_value=target_due.isoformat(timespec="seconds") if hasattr(target_due,"isoformat") else target_due
        existing=next((todo for todo in pending if todo["id"] not in used and todo["task_type"]==task_type and todo["source_stage"]==source_stage),None)
        if existing:
            db.execute("UPDATE todos SET title=?,due_at=?,updated_at=? WHERE id=?",(title,due_value,now,existing["id"]))
            used.add(existing["id"])
        else:
            _add(db,app_id,title,task_type,source_stage,target_due)
    for todo in pending:
        if todo["id"] not in used:
            db.execute("UPDATE todos SET status='cancelled',updated_at=? WHERE id=?",(now,todo["id"]))

def reconcile_auto_todos(db):
    for app in db.all("SELECT * FROM applications"):
        sync_auto_todos(db,app)

def change_status(db, application_id: int, new_status: str, next_event_at=None):
    app=db.one("SELECT * FROM applications WHERE id=?",(application_id,))
    if not app: raise KeyError(application_id)
    old=app["current_status"]; now=db.now()
    if old != new_status:
        db.execute("DELETE FROM todo_dismissals WHERE application_id=?",(application_id,))
    db.execute("UPDATE applications SET current_status=?,next_event_at=?,updated_at=?,last_status_changed_at=? WHERE id=?", (new_status,next_event_at or None,now,now,application_id))
    if old != new_status:
        db.execute("INSERT INTO status_history(application_id,old_status,new_status,changed_at) VALUES(?,?,?,?)",(application_id,old,new_status,now))
    app=db.one("SELECT * FROM applications WHERE id=?",(application_id,)); sync_auto_todos(db,app)
    return app
