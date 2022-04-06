import datetime

from ckl.date import to_oa_date, to_date, is_leap_year

def test_is_leap_year_1():
    assert(is_leap_year(1999) == False)

def test_is_leap_year_2():
    assert(is_leap_year(1980) == True)

def test_is_leap_year_3():
    assert(is_leap_year(1900) == False)

def test_is_leap_year_4():
    assert(is_leap_year(2000) == True)

def test_to_oa_date_1():
    assert(to_oa_date(datetime.datetime(1970, 1, 1)) == 25569)

def test_to_oa_date_2():
    assert(to_oa_date(datetime.datetime(2000, 6, 1)) == 36678)

def test_to_oa_date_3():
    assert(to_oa_date(datetime.datetime(2000, 6, 10)) == 36687)

def test_to_oa_date_4():
    assert(to_oa_date(datetime.datetime(1970, 1, 1, 12)) == 25569.5)

def test_to_oa_date_5():
    assert(to_oa_date(datetime.datetime(2000, 6, 1, 12)) == 36678.5)

def test_to_oa_date_6():
    assert(to_oa_date(datetime.datetime(2000, 6, 1, 12, 48, 36)) == 36678.53375)

def test_to_oa_date_7():
    assert(to_oa_date(datetime.datetime(2000, 6, 1, 12, 48, 36, 444000)) == 36678.533755138895)

def test_to_date_1():
    assert(to_date(25569) == datetime.datetime(1970, 1, 1))

def test_to_date_2():
    assert(to_date(36678) == datetime.datetime(2000, 6, 1))

def test_to_date_3():
    assert(to_date(36687) == datetime.datetime(2000, 6, 10))

def test_to_date_4():
    assert(to_date(25569.5) == datetime.datetime(1970, 1, 1, 12))

def test_to_date_5():
    assert(to_date(36678.5) == datetime.datetime(2000, 6, 1, 12))

def test_to_date_6():
    assert(to_date(36678.53375) == datetime.datetime(2000, 6, 1, 12, 48, 36))

def test_to_date_7():
    assert(to_date(36678.533755138895) == datetime.datetime(2000, 6, 1, 12, 48, 36, 444000))

def test_round_trip():
    assert(to_date(to_oa_date(datetime.datetime(2017, 4, 5))) == datetime.datetime(2017, 4, 5))

def test_round_trip_minus_3():
    assert(to_date(to_oa_date(datetime.datetime(2017, 4, 5)) - 3) == datetime.datetime(2017, 4, 2))
