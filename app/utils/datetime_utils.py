from datetime import datetime
import pytz

VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")


def utc_to_vn(dt: datetime | None) -> str | None:
    
    if dt is None:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.utc)

    vn_time = dt.astimezone(VN_TZ)
    return vn_time.strftime("%Y-%m-%d %H:%M:%S")


def now_vn() -> str:
   
    return datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")
