from __future__ import annotations

import json, os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.api.jd_clip import configure_jd_clipper, router as jd_clip_router
from app.database.db import configure_db
from app.services.application_service import STATUSES, enrich_app, sort_applications, upcoming_interviews, update_application
from app.services.backup_service import backup_database
from app.services.feishu_service import FeishuService, extract_url
from app.services.job_pool_service import POOL_STATUSES, delete_job_pool, display_pool_status, update_job_pool_status
from app.services.jd_library_service import scan_jds, start_watcher
from app.services.todo_service import add_todo, change_status, delete_todo, reconcile_auto_todos, toggle_todo
from app.services.urgency_service import urgency

ROOT=Path(__file__).resolve().parents[1]
SETTINGS_PATH=ROOT/"config/settings.json"
settings=json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
PRODUCT_NAME=settings.get("product_name","本地求职工作台")
db=configure_db(settings["database"],settings["timezone"])
configure_jd_clipper(settings.get("jd_clipper_directory",str(Path(settings["jd_directory"]).parent)),settings["log_directory"],settings["timezone"])
templates=Jinja2Templates(directory=str(ROOT/"app/templates"))
watcher=None

def ctx(request, **extra):
    return {"request":request,"product":PRODUCT_NAME,"active":extra.pop("active", ""),"statuses":STATUSES,"settings":settings,**extra}

@asynccontextmanager
async def lifespan(app):
    global watcher
    backup_database(settings["database"],settings["backup_directory"],timezone=settings["timezone"])
    scan_jds(db,settings["jd_directory"])
    reconcile_auto_todos(db)
    try: watcher=start_watcher(db,settings["jd_directory"])
    except Exception: watcher=None
    yield
    if watcher: watcher.stop(); watcher.join(timeout=3)

app=FastAPI(title=PRODUCT_NAME,lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"chrome-extension://.*",
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.include_router(jd_clip_router)
app.mount("/static",StaticFiles(directory=str(ROOT/"app/static")),name="static")

def apps(): return [enrich_app(x,settings["timezone"]) for x in db.all("SELECT * FROM applications ORDER BY COALESCE(next_event_at,'9999'),updated_at DESC")]

@app.get("/",response_class=HTMLResponse)
def dashboard(request:Request):
    all_apps=apps(); pool=db.all("SELECT * FROM job_pool ORDER BY CASE priority WHEN 'S' THEN 1 WHEN 'A' THEN 2 ELSE 3 END, deadline")
    for item in pool:item["display_status"]=display_pool_status(item)
    now=datetime.now(ZoneInfo(settings["timezone"]))
    todos=db.all("SELECT t.*,a.company,a.position,a.current_status FROM todos t LEFT JOIN applications a ON a.id=t.application_id WHERE t.status='pending' ORDER BY COALESCE(t.due_at,'9999')")
    for t in todos:t["urgency"]=urgency(t["due_at"],settings["timezone"])
    counts={s:sum(1 for a in all_apps if a["current_status"]==s) for s in STATUSES}
    advancing=sum(counts.get(x,0) for x in ["测评","笔试","群面","一面","二面","三面","终面","HR面","人才库"])
    interviews=sum(1 for a in upcoming_interviews(all_apps,settings["timezone"],now) if a["within_7_days"])
    recommended=[x for x in pool if x["priority"] in {"S","A"} and x["application_recommendation"] in {"重点投","建议投"} and x["display_status"] not in {"已投递","不合适"}][:6]
    history=db.all("SELECT h.*,a.company,a.position FROM status_history h JOIN applications a ON a.id=h.application_id ORDER BY h.changed_at DESC LIMIT 8")
    kpis={"pool":len(pool),"applied":len(all_apps),"advancing":advancing,"interviews":interviews,"offer":counts.get("Offer",0)}
    return templates.TemplateResponse("dashboard.html",ctx(request,active="dashboard",kpis=kpis,todos=todos,counts=counts,recommended=recommended,history=history))

@app.get("/job-pool",response_class=HTMLResponse)
def job_pool(request:Request,q:str="",priority:str="",city:str=""):
    rows=db.all("SELECT * FROM job_pool ORDER BY CASE priority WHEN 'S' THEN 1 WHEN 'A' THEN 2 WHEN 'B' THEN 3 ELSE 4 END, deadline")
    for row in rows:
        row["application_url"]=extract_url(row.get("jd_url")); row["display_status"]=display_pool_status(row)
    if q: rows=[r for r in rows if q.casefold() in (r["company"]+r["position"]).casefold()]
    if priority: rows=[r for r in rows if r["priority"]==priority]
    if city: rows=[r for r in rows if city in r["city"]]
    cities=sorted({x["city"] for x in db.all("SELECT city FROM job_pool") if x["city"]})
    return templates.TemplateResponse("job_pool.html",ctx(request,active="pool",rows=rows,cities=cities,filters={"q":q,"priority":priority,"city":city},pool_statuses=POOL_STATUSES))

@app.get("/job-pool/{job_id}",response_class=HTMLResponse)
def job_pool_detail(request:Request,job_id:int):
    row=db.one("SELECT * FROM job_pool WHERE id=?",(job_id,))
    if not row: raise HTTPException(404)
    row["application_url"]=extract_url(row.get("jd_url")); row["display_status"]=display_pool_status(row)
    return templates.TemplateResponse("job_pool_detail.html",ctx(request,active="pool",job=row))

@app.post("/job-pool/{job_id}/delete")
def job_pool_delete(job_id:int):
    try: delete_job_pool(db,job_id)
    except KeyError: raise HTTPException(404,"岗位不存在")
    return RedirectResponse("/job-pool?deleted=1",303)

@app.post("/job-pool/{job_id}/status")
def job_pool_status(job_id:int,pool_status:str=Form(...)):
    try: update_job_pool_status(db,job_id,pool_status)
    except KeyError: raise HTTPException(404,"岗位不存在")
    except ValueError as exc: raise HTTPException(400,str(exc))
    return RedirectResponse("/job-pool?saved=1",303)

@app.get("/applications",response_class=HTMLResponse)
def applications(request:Request,q:str="",status:str="",sort:str="",dir:str="asc"):
    rows=apps()
    if q: rows=[r for r in rows if q.casefold() in (r["company"]+r["position"]+r["city"]).casefold()]
    if status: rows=[r for r in rows if r["current_status"]==status or (status=="面试中" and r["current_status"] in {"群面","一面","二面","三面","终面","HR面"}) or (status=="已结束" and r["current_status"] in {"Offer","未通过","主动放弃"})]
    rows=sort_applications(rows,sort,dir)
    counts={s:sum(1 for a in rows if a["current_status"]==s) for s in STATUSES}
    history=db.all("SELECT h.*,a.company,a.position FROM status_history h JOIN applications a ON a.id=h.application_id ORDER BY h.changed_at DESC LIMIT 6")
    funnel=[("已投递",len(rows)),("测评/笔试",sum(counts.get(x,0) for x in ["测评","笔试"])),("进入面试",sum(counts.get(x,0) for x in ["群面","一面","二面","三面","终面","HR面","Offer"])),("二面及以上",sum(counts.get(x,0) for x in ["二面","三面","终面","HR面","Offer"])),("Offer",counts.get("Offer",0))]
    return templates.TemplateResponse("applications.html",ctx(request,active="applications",rows=rows,counts=counts,history=history,funnel=funnel,filters={"q":q,"status":status,"sort":sort,"dir":dir},resumes=scan_resumes()))

@app.get("/applications/{app_id}",response_class=HTMLResponse)
def application_detail(request:Request,app_id:int):
    item=db.one("SELECT * FROM applications WHERE id=?",(app_id,))
    if not item: raise HTTPException(404)
    item=enrich_app(item,settings["timezone"])
    history=db.all("SELECT * FROM status_history WHERE application_id=? ORDER BY changed_at DESC",(app_id,))
    todos=db.all("SELECT * FROM todos WHERE application_id=? ORDER BY status,COALESCE(due_at,'9999')",(app_id,))
    resumes=scan_resumes()
    prompt=f"""请作为求职面试教练，为以下岗位生成系统化面试准备方案。\n公司：{item['company']}\n岗位：{item['position']}\n业务线：{item['business']}\n当前轮次：{item['current_status']}\n投递简历：{item['resume_filename'] or '未绑定'}\n\n完整 JD：\n{item['jd_content']}\n\n请输出：岗位核心职责、准备方向、简历深挖问题、岗位专业问题、公司/业务问题、行为面试问题、复习知识点与模拟回答建议。"""
    return templates.TemplateResponse("application_detail.html",ctx(request,active="applications",app=item,history=history,todos=todos,resumes=resumes,prompt=prompt))

def valid_resume_path(resume_path:str):
    if resume_path and resume_path not in {r["path"] for r in scan_resumes()}:
        raise HTTPException(400,"简历路径不在指定简历库中")
    return resume_path

@app.post("/applications/{app_id}/update")
def application_update(app_id:int,company:str=Form(...),position:str=Form(...),business:str=Form(""),city:str=Form(""),current_status:str=Form(...),next_action:str=Form(""),next_event_at:str=Form(""),applied_date:str=Form(""),resume_path:str=Form(""),notes:str=Form(""),prep_content:str=Form("")):
    try:
        update_application(db,app_id,company=company.strip(),position=position.strip(),business=business.strip(),city=city.strip(),current_status=current_status,next_action=next_action.strip(),next_event_at=next_event_at or None,applied_date=applied_date or None,resume_path=valid_resume_path(resume_path),notes=notes,prep_content=prep_content)
    except (KeyError,ValueError) as exc: raise HTTPException(400,str(exc))
    return RedirectResponse(f"/applications/{app_id}",303)

@app.post("/applications/{app_id}/quick-update")
def application_quick_update(app_id:int,city:str=Form(""),current_status:str=Form(...),next_action:str=Form(""),next_event_at:str=Form(""),resume_path:str=Form("")):
    try:
        update_application(db,app_id,city=city.strip(),current_status=current_status,next_action=next_action.strip(),next_event_at=next_event_at or None,resume_path=valid_resume_path(resume_path))
    except (KeyError,ValueError) as exc: raise HTTPException(400,str(exc))
    return RedirectResponse("/applications?saved=1",303)

@app.get("/todos",response_class=HTMLResponse)
def todo_page(request:Request):
    rows=db.all("SELECT t.*,a.company,a.position,a.current_status FROM todos t LEFT JOIN applications a ON a.id=t.application_id WHERE t.status IN ('pending','completed') ORDER BY CASE t.status WHEN 'pending' THEN 1 ELSE 2 END,COALESCE(t.due_at,'9999')")
    now=datetime.now(ZoneInfo(settings["timezone"]))
    groups={"今天":[],"未来3天":[],"未来7天":[],"待补时间":[],"已完成":[]}
    for t in rows:
        t["urgency"]=urgency(t["due_at"],settings["timezone"])
        if t["status"]=="completed":groups["已完成"].append(t)
        elif not t["due_at"]:groups["待补时间"].append(t)
        else:
            dt=datetime.fromisoformat(t["due_at"]); days=(dt.date()-now.date()).days
            if days<=0:groups["今天"].append(t)
            elif days<=3:groups["未来3天"].append(t)
            else:groups["未来7天"].append(t)
    return templates.TemplateResponse("todos.html",ctx(request,active="todos",groups=groups,applications=apps()))

@app.post("/todos/add")
def todo_add(title:str=Form(...),application_id:str=Form(""),due_at:str=Form("")):
    try: add_todo(db,title,int(application_id) if application_id else None,due_at or None)
    except ValueError as exc: raise HTTPException(400,str(exc))
    return RedirectResponse("/todos?created=1",303)
@app.post("/todos/{todo_id}/complete")
def todo_complete(todo_id:int):
    try: toggle_todo(db,todo_id)
    except KeyError: raise HTTPException(404,"待办不存在")
    return RedirectResponse("/todos",303)

@app.post("/todos/{todo_id}/delete")
def todo_delete(todo_id:int):
    try: delete_todo(db,todo_id)
    except KeyError: raise HTTPException(404,"待办不存在")
    return RedirectResponse("/todos?deleted=1",303)

@app.get("/interviews",response_class=HTMLResponse)
def interviews(request:Request):
    rows=upcoming_interviews(apps(),settings["timezone"])
    return templates.TemplateResponse("interviews.html",ctx(request,active="interviews",rows=rows))

def scan_resumes():
    rows=[]
    for p in sorted(Path(settings["resume_directory"]).iterdir()):
        if p.is_file() and p.suffix.lower() in {".pdf",".docx"}: rows.append({"path":str(p.resolve()),"name":p.name,"type":p.suffix[1:].upper(),"modified":datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")})
    return rows
@app.get("/resumes",response_class=HTMLResponse)
def resumes(request:Request): return templates.TemplateResponse("resumes.html",ctx(request,active="resumes",rows=scan_resumes()))
@app.get("/resumes/open")
def resume_open(path:str):
    target=Path(path).resolve(); root=Path(settings["resume_directory"]).resolve()
    if root not in target.parents or target.suffix.lower() not in {".pdf",".docx"}: raise HTTPException(403)
    os.system(f"open {json.dumps(str(target))}")
    return RedirectResponse("/resumes",303)

@app.get("/settings",response_class=HTMLResponse)
def settings_page(request:Request):
    service=FeishuService(settings); status=service.status()
    return templates.TemplateResponse("settings.html",ctx(request,active="settings",feishu_status=status,last_sync=db.get_setting("last_feishu_sync")))
@app.post("/actions/scan-jd")
def action_scan_jd(): scan_jds(db,settings["jd_directory"]); return RedirectResponse("/settings?ok=jd",303)
@app.post("/actions/backup")
def action_backup(): backup_database(settings["database"],settings["backup_directory"],timezone=settings["timezone"]); return RedirectResponse("/settings?ok=backup",303)
@app.post("/actions/sync-feishu")
def action_sync_feishu():
    try: count=FeishuService(settings).sync(db); return RedirectResponse(f"/job-pool?synced={count}",303)
    except Exception as exc: return RedirectResponse(f"/settings?error={str(exc)}",303)

@app.get("/health")
def health(): return {"ok":True,"product":PRODUCT_NAME,"database":str(db.path)}
