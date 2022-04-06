import datetime
import math

DAYS_PER_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
DAYS_EPOCH = 25569

def is_leap_year(year):
    return (year % 4 == 0) and ((year % 100 != 0) or (year % 400 == 0))

def year_days(year):
    return 366 if is_leap_year(year) else 365

def month_days(year, month):
    return 29 if is_leap_year(year) and month == 1 else DAYS_PER_MONTH[month]

def to_oa_date(date):
    year = date.year
    result = 1
    for y in range(1900, year):
        result += year_days(y)
    month = date.month - 1
    for m in range(month):
        result += month_days(year, m)
    result += date.day
    result += date.hour / 24
    result += date.minute / 24 / 60
    result += date.second / 24 / 60 / 60
    result += date.microsecond / 24 / 60 / 60 / 1000 / 1000
    return result

def to_date(oadate):
    value = oadate - DAYS_EPOCH
    year = 1970
    while value > year_days(year):
        value -= year_days(year)
        year += 1
    month = 0
    while value >= month_days(year, month):
        value -= month_days(year, month)
        month += 1
    day = math.trunc(value) + 1
    value = value - math.trunc(value)
    hours = math.trunc(value * 24)
    value = value * 24 - hours
    minutes = math.trunc(value * 60)
    value = value * 60 - minutes
    seconds = math.trunc(value * 60)
    value = value * 60 - seconds
    microseconds = math.trunc(value * 1000 * 1000)
    result = datetime.datetime.fromtimestamp(0)
    return result.replace(
            year=year,
            month=month+1,
            day=day,
            hour=hours,
            minute=minutes,
            second=seconds,
            microsecond=microseconds
    )
