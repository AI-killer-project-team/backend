from typing import List


def average(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def std_dev(values: List[float]) -> float:
    if not values:
        return 0.0
    avg = average(values)
    variance = sum((v - avg) ** 2 for v in values) / len(values)
    return variance ** 0.5
