from datetime import datetime
from zoneinfo import ZoneInfo

def urgency(next_event_at, timezone="Asia/Shanghai", now=None):
    if not next_event_at: return {"key":"missing","label":"待补时间","icon":"⚪","seconds":None}
    try:
        dt = datetime.fromisoformat(next_event_at)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=ZoneInfo(timezone))
    except (ValueError, TypeError): return {"key":"missing","label":"待补时间","icon":"⚪","seconds":None}
    now = now or datetime.now(ZoneInfo(timezone))
    seconds = (dt-now).total_seconds()
    if seconds < 0: key,label,icon="overdue","已逾期","🚨"
    elif seconds <= 86400: key,label,icon="urgent","紧急","🔴"
    elif seconds <= 259200: key,label,icon="high","高","🟠"
    elif seconds <= 604800: key,label,icon="normal","正常","🟡"
    else: key,label,icon="relaxed","宽松","🟢"
    return {"key":key,"label":label,"icon":icon,"seconds":seconds}

