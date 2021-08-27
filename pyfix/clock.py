from datetime import datetime, timezone

def SystemClock():
    return datetime.now(timezone.utc)

def set_manual_clock(d):
    global clock
    clock = lambda: d

clock = SystemClock
