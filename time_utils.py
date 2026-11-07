from datetime import datetime

def zambia_now():
    """
    Return the current Zambia local time as a naive datetime.

    The project database uses naive DateTime columns, and the
    Android/Termux system clock is already configured for Zambia
    time (UTC+2).
    """
    return datetime.now()
