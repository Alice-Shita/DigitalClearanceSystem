from datetime import datetime
from zoneinfo import ZoneInfo

def zambia_now():
    return datetime.now(ZoneInfo("Africa/Lusaka")).replace(tzinfo=None)
