from datetime import datetime


def elapsed_seconds(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds()
