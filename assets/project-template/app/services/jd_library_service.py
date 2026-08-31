from __future__ import annotations
import json
import threading
from pathlib import Path
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from app.parsers.jd_parser import normalize_url, parse_jd_file

def _same(a,b): return (a or "").strip().casefold()==(b or "").strip().casefold()

def find_job_pool_match(db, item):
    rows=db.all("SELECT * FROM job_pool")
    url=normalize_url(item.get("source_url",""))
    if url:
        for r in rows:
            if normalize_url(r.get("jd_url",""))==url: return r
    if item.get("external_job_id"):
        for r in rows:
            if _same(r.get("external_job_id"),item["external_job_id"]): return r
    for r in rows:
        if _same(r.get("company"),item["company"]) and _same(r.get("position"),item["position"]): return r
    return None

def import_jd(db, path: str):
    item=parse_jd_file(path)
    existing=None
    if item["source_url"]: existing=db.one("SELECT * FROM applications WHERE source_url=?",(item["source_url"],))
    if not existing and item["external_job_id"]: existing=db.one("SELECT * FROM applications WHERE external_job_id=?",(item["external_job_id"],))
    if not existing: existing=db.one("SELECT * FROM applications WHERE company=? AND position=?",(item["company"],item["position"]))
    if not existing: existing=db.one("SELECT * FROM applications WHERE raw_title=?",(item["raw_title"],))
    now=db.now(); match=find_job_pool_match(db,item)
    if existing:
        app_id=existing["id"]
        try: locked=set(json.loads(existing.get("manual_fields") or "[]"))
        except (TypeError,ValueError): locked=set()
        values={
            "external_job_id":item["external_job_id"],"raw_title":item["raw_title"],"source_url":item["source_url"],
            "jd_file_path":item["jd_file_path"],"jd_content":item["jd_content"],"jd_content_hash":item["jd_content_hash"],
            "updated_at":now,
        }
        for field in ("company","position","business","city"):
            if field not in locked: values[field]=item[field]
        assignments=",".join(f"{key}=?" for key in values)
        db.execute(f"UPDATE applications SET {assignments},job_pool_id=COALESCE(job_pool_id,?) WHERE id=?",(*values.values(),match["id"] if match else None,app_id))
    else:
        app_id=db.execute("INSERT INTO applications(job_pool_id,company,position,business,city,external_job_id,raw_title,source_url,jd_file_path,jd_content,jd_content_hash,applied_date,current_status,created_at,updated_at,last_status_changed_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?, '已投递',?,?,?)", (match["id"] if match else None,item["company"],item["position"],item["business"],item["city"],item["external_job_id"],item["raw_title"],item["source_url"],item["jd_file_path"],item["jd_content"],item["jd_content_hash"],item["clipped_date"],now,now,now))
        db.execute("INSERT INTO status_history(application_id,old_status,new_status,changed_at) VALUES(?,NULL,'已投递',?)",(app_id,now))
    db.execute("INSERT INTO imported_files(file_path,file_hash,last_modified,application_id,imported_at) VALUES(?,?,?,?,?) ON CONFLICT(file_path) DO UPDATE SET file_hash=excluded.file_hash,last_modified=excluded.last_modified,application_id=excluded.application_id,imported_at=excluded.imported_at",(item["jd_file_path"],item["jd_content_hash"],item["last_modified"],app_id,now))
    if match: db.execute("UPDATE job_pool SET linked_application_id=?,updated_at=? WHERE id=?",(app_id,now,match["id"]))
    return app_id

def scan_jds(db, directory):
    result=[]
    for p in sorted(Path(directory).rglob("*.md")):
        try: result.append(import_jd(db,str(p)))
        except Exception as exc: result.append({"file":str(p),"error":str(exc)})
    return result

class Handler(FileSystemEventHandler):
    def __init__(self,db): self.db=db; self._timers={}
    def _queue(self,path):
        if not str(path).lower().endswith(".md"): return
        old=self._timers.pop(path,None)
        if old: old.cancel()
        timer=threading.Timer(.6,lambda: import_jd(self.db,path) if Path(path).exists() else None)
        self._timers[path]=timer; timer.daemon=True; timer.start()
    def on_created(self,event):
        if not event.is_directory:self._queue(event.src_path)
    def on_modified(self,event):
        if not event.is_directory:self._queue(event.src_path)

def start_watcher(db,directory):
    observer=Observer(); observer.schedule(Handler(db),directory,recursive=True); observer.daemon=True; observer.start(); return observer
