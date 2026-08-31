from __future__ import annotations
import json, os, re, shutil, subprocess
from pathlib import Path

FIELDS = ["岗位名称","公司名称","业务线/部门","城市","岗位方向","职位ID","JD链接","截止日期","来源","优先级","投递建议","岗位匹配点","风险点","长期壁垒","长期壁垒说明","AI替代风险","岗位池状态","JD原文","备注"]
MAP={"岗位名称":"position","公司名称":"company","业务线/部门":"business","城市":"city","岗位方向":"job_direction","职位ID":"external_job_id","JD链接":"jd_url","截止日期":"deadline","来源":"source","优先级":"priority","投递建议":"application_recommendation","岗位匹配点":"match_points","风险点":"risk_points","长期壁垒":"career_moat","长期壁垒说明":"career_moat_description","AI替代风险":"ai_replacement_risk","岗位池状态":"pool_status","JD原文":"jd_text","备注":"notes"}

def _scalar(value):
    if isinstance(value,list): return "、".join(str(x.get("text") or x.get("name") or x) if isinstance(x,dict) else str(x) for x in value)
    if isinstance(value,dict): return value.get("text") or value.get("name") or value.get("link") or json.dumps(value,ensure_ascii=False)
    return "" if value is None else str(value)

def extract_url(value):
    """从飞书链接字段、Markdown 链接或普通文本中提取实际 http(s) 地址。"""
    if isinstance(value,list):
        for item in value:
            url=extract_url(item)
            if url:return url
        return ""
    if isinstance(value,dict):
        for key in ("link","url","href","text","name"):
            url=extract_url(value.get(key))
            if url:return url
        return ""
    text="" if value is None else str(value).strip()
    markdown=re.search(r"\]\((https?://[^)]+)\)",text,re.I)
    if markdown:return markdown.group(1).strip()
    bare=re.search(r"https?://[^\s<>\]]+",text,re.I)
    return bare.group(0).rstrip(")。，,;") if bare else ""

class FeishuService:
    def __init__(self,settings): self.settings=settings
    def command(self):
        configured=self.settings.get("feishu",{}).get("cli_path","")
        if configured and Path(configured).exists(): return configured
        return shutil.which("lark-cli")
    def _run(self,args,timeout=60):
        cmd=self.command()
        if not cmd: raise RuntimeError("未找到 lark-cli；请从包含 Node.js 的终端启动工作台")
        env=os.environ.copy(); env["LARKSUITE_CLI_NO_UPDATE_NOTIFIER"]="1"; env["LARKSUITE_CLI_NO_SKILLS_NOTIFIER"]="1"
        proc=subprocess.run([cmd,*args],capture_output=True,text=True,timeout=timeout,env=env)
        text=proc.stdout.strip() or proc.stderr.strip()
        try: payload=json.loads(text)
        except Exception: raise RuntimeError(text or f"lark-cli 退出码 {proc.returncode}")
        if proc.returncode or payload.get("ok") is False: raise RuntimeError(payload.get("error",{}).get("message") or text)
        return payload
    def status(self):
        try:
            p=self._run(["auth","status","--json","--verify"]); data=p.get("data",p)
            user=data.get("identities",{}).get("user",{})
            connected=bool(data.get("verified") and user.get("verified") and user.get("tokenStatus")=="valid")
            return {"connected":connected,"message":f'用户登录有效 · {user.get("userName", "飞书用户")}' if connected else "用户登录待检查","detail":data}
        except Exception as e: return {"connected":False,"message":str(e)}
    def fields(self):
        f=self.settings["feishu"]
        p=self._run(["base","+field-list","--base-token",f["base_token"],"--table-id",f["table_id"],"--as","user"])
        data=p.get("data",{}); return data.get("items") or data.get("fields") or (data if isinstance(data,list) else [])
    def records(self):
        f=self.settings["feishu"]
        args=["base","+record-list","--base-token",f["base_token"],"--table-id",f["table_id"],"--view-id",f.get("view_id") or f["view_name"],"--limit","200","--as","user","--json"]
        payload=self._run(args).get("data",{})
        matrix=payload.get("data",[]); names=payload.get("fields",[]); ids=payload.get("record_id_list",[])
        return [{"record_id":ids[i],"fields":dict(zip(names,row))} for i,row in enumerate(matrix)]
    def sync(self,db):
        records=self.records(); now=db.now(); count=0
        for rec in records:
            fields=rec.get("fields",rec); rid=rec.get("record_id") or rec.get("id")
            if db.one("SELECT 1 FROM job_pool_dismissals WHERE feishu_record_id=?",(rid,)):
                continue
            values={MAP[k]:(extract_url(fields.get(k)) if k=="JD链接" else _scalar(fields.get(k))) for k in FIELDS}
            cols=list(values); placeholders=",".join("?" for _ in cols)
            updates=",".join(f"{c}=excluded.{c}" for c in cols)
            db.execute(f"INSERT INTO job_pool(feishu_record_id,{','.join(cols)},last_synced_at,created_at,updated_at) VALUES(?,{placeholders},?,?,?) ON CONFLICT(feishu_record_id) DO UPDATE SET {updates},last_synced_at=excluded.last_synced_at,updated_at=excluded.updated_at",(rid,*[values[c] for c in cols],now,now,now))
            count+=1
        db.set_setting("last_feishu_sync",now); return count
