from app.database.db import Database
from app.services.job_pool_service import POOL_STATUSES, display_pool_status, update_job_pool_status
from app.services.todo_service import add_todo, toggle_todo


def test_database_and_local_status(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    now = db.now()
    job_id = db.execute(
        "INSERT INTO job_pool(feishu_record_id,company,position,pool_status,created_at,updated_at) VALUES(?,?,?,?,?,?)",
        ("example-record", "示例公司", "示例岗位", "待评估", now, now),
    )
    assert POOL_STATUSES == ["待投递", "已投递", "不合适"]
    assert display_pool_status(db.one("SELECT * FROM job_pool WHERE id=?", (job_id,))) == "待投递"
    update_job_pool_status(db, job_id, "不合适")
    assert display_pool_status(db.one("SELECT * FROM job_pool WHERE id=?", (job_id,))) == "不合适"


def test_manual_todo_can_be_reopened(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    todo_id = add_todo(db, "准备示例任务", due_at=db.now())
    assert toggle_todo(db, todo_id) == "completed"
    assert toggle_todo(db, todo_id) == "pending"
