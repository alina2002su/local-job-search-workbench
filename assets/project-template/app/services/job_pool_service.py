POOL_STATUSES=["待投递","已投递","不合适"]

def display_pool_status(job):
    local=(job.get("local_pool_status") or "").strip()
    if local in POOL_STATUSES:
        return local
    if job.get("linked_application_id"):
        return "已投递"
    remote=(job.get("pool_status") or "").strip()
    if remote=="已决定不投":
        return "不合适"
    return remote if remote in POOL_STATUSES else "待投递"

def update_job_pool_status(db, job_id: int, status: str):
    if status not in POOL_STATUSES:
        raise ValueError("无效的岗位池状态")
    if not db.one("SELECT id FROM job_pool WHERE id=?",(job_id,)):
        raise KeyError(job_id)
    db.execute("UPDATE job_pool SET local_pool_status=?,updated_at=? WHERE id=?",(status,db.now(),job_id))

def delete_job_pool(db, job_id: int):
    """删除本地岗位池记录，并阻止同一条飞书记录在后续同步时重新出现。"""
    job=db.one("SELECT id,feishu_record_id FROM job_pool WHERE id=?",(job_id,))
    if not job:
        raise KeyError(job_id)
    db.execute("INSERT OR REPLACE INTO job_pool_dismissals(feishu_record_id,deleted_at) VALUES(?,?)",
               (job["feishu_record_id"],db.now()))
    db.execute("DELETE FROM job_pool WHERE id=?",(job_id,))
