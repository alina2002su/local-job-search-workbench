import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from .urgency_service import urgency
from .todo_service import change_status

STATUSES=["已投递","测评","笔试","群面","一面","二面","三面","终面","HR面","Offer","人才库","未通过","主动放弃"]
INTERVIEW_STAGES={"群面","一面","二面","三面","终面","HR面"}

SORTABLE_APPLICATION_FIELDS={"company","city","applied_date","current_status","next_action","next_event_at","urgency","resume"}

_PINYIN_BOUNDS=[(-20319,"a"),(-20284,"b"),(-19776,"c"),(-19219,"d"),(-18711,"e"),(-18527,"f"),(-18240,"g"),(-17923,"h"),(-17418,"j"),(-16475,"k"),(-16213,"l"),(-15641,"m"),(-15166,"n"),(-14923,"o"),(-14915,"p"),(-14631,"q"),(-14150,"r"),(-14091,"s"),(-13319,"t"),(-12839,"w"),(-12557,"x"),(-11848,"y"),(-11056,"z")]

def _text_initial_key(text):
    """生成适合公司/城市首字母排序的轻量键，不依赖额外运行库。"""
    result=[]
    for char in str(text or "").casefold():
        try:
            encoded=char.encode("gbk")
        except UnicodeEncodeError:
            result.append(char); continue
        if len(encoded)<2:
            result.append(char); continue
        code=encoded[0]*256+encoded[1]-65536
        initial=next((letter for index,(bound,letter) in enumerate(_PINYIN_BOUNDS) if code>=bound and (index==len(_PINYIN_BOUNDS)-1 or code<_PINYIN_BOUNDS[index+1][0])),char)
        result.append(initial)
    return "".join(result)

def sort_applications(applications, field="", direction="asc"):
    """服务端排序兜底；空值始终放在最后。"""
    if field not in SORTABLE_APPLICATION_FIELDS:
        return list(applications)
    direction="desc" if direction=="desc" else "asc"
    stages={name:index for index,name in enumerate(STATUSES,1)}
    urgency_order={"missing":0,"relaxed":1,"normal":2,"high":3,"urgent":4,"overdue":5}
    def raw_value(app):
        if field=="company": return f'{app.get("company") or ""} {app.get("position") or ""}'.strip()
        if field=="resume": return app.get("resume_filename") or ""
        if field=="urgency": return (app.get("urgency") or {}).get("key","")
        return app.get(field) or ""
    def value(app):
        raw=raw_value(app)
        if field in {"current_status","next_action"}: return stages.get(raw,0)
        if field=="urgency": return urgency_order.get(raw,0)
        return _text_initial_key(raw)
    filled=[app for app in applications if raw_value(app)]
    empty=[app for app in applications if not raw_value(app)]
    return sorted(filled,key=value,reverse=direction=="desc")+empty

def upcoming_interviews(applications, timezone="Asia/Shanghai", now=None):
    """返回所有尚未到期、已明确安排面试轮次和时间的岗位。"""
    tz=ZoneInfo(timezone)
    now=now or datetime.now(tz)
    if now.tzinfo is None:
        now=now.replace(tzinfo=tz)
    result=[]
    for app in applications:
        next_action=(app.get("next_action") or "").strip()
        # “下一安排”描述的是 next_event_at；未填写时才回退到当前进度。
        stage=next_action if next_action in INTERVIEW_STAGES else (
            app.get("current_status") if not next_action and app.get("current_status") in INTERVIEW_STAGES else ""
        )
        if not stage or not app.get("next_event_at"):
            continue
        try:
            interview_at=datetime.fromisoformat(app["next_event_at"])
        except (TypeError, ValueError):
            continue
        if interview_at.tzinfo is None:
            interview_at=interview_at.replace(tzinfo=tz)
        if interview_at < now:
            continue
        row=dict(app)
        row["interview_stage"]=stage
        row["interview_at"]=interview_at
        row["within_7_days"]=interview_at <= now+timedelta(days=7)
        result.append(row)
    return sorted(result,key=lambda item:item["interview_at"])

def enrich_app(app, timezone="Asia/Shanghai"):
    app=dict(app); app["urgency"]=urgency(app.get("next_event_at"),timezone)
    app["jd_missing"]=bool(app.get("jd_file_path") and not Path(app["jd_file_path"]).exists())
    app["resume_missing"]=bool(app.get("resume_path") and not Path(app["resume_path"]).exists())
    return app

def update_application(db, application_id: int, *, current_status: str, next_event_at=None,
                       resume_path="", company=None, position=None, business=None, city=None,
                       applied_date=None, next_action=None, notes=None, prep_content=None):
    """更新用户可编辑的本地字段；JD 路径、正文和哈希不会在此更新。"""
    if current_status not in STATUSES:
        raise ValueError("无效的招聘阶段")
    if next_action is not None and next_action not in ["", *STATUSES]:
        raise ValueError("无效的下一安排")
    existing=db.one("SELECT id,manual_fields FROM applications WHERE id=?",(application_id,))
    if not existing:
        raise KeyError(application_id)
    values={"resume_path":resume_path or "","resume_filename":Path(resume_path).name if resume_path else ""}
    optional={"company":company,"position":position,"business":business,"city":city,
              "applied_date":applied_date,"next_action":next_action,"notes":notes,"prep_content":prep_content}
    values.update({key:value for key,value in optional.items() if value is not None})
    try: locked=set(json.loads(existing.get("manual_fields") or "[]"))
    except (TypeError,ValueError): locked=set()
    locked.update(key for key in ("company","position","business","city") if optional[key] is not None)
    values["manual_fields"]=json.dumps(sorted(locked),ensure_ascii=False)
    values["updated_at"]=db.now()
    assignments=",".join(f"{key}=?" for key in values)
    db.execute(f"UPDATE applications SET {assignments} WHERE id=?",(*values.values(),application_id))
    return change_status(db,application_id,current_status,next_event_at or None)
