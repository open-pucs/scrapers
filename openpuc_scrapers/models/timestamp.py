import json
from typing import Annotated, List, Union
from datetime import date, datetime, timezone

from pydantic import BeforeValidator, PlainSerializer


#
# class RFC3339TimeClass:
#
#     def __init__(self, time_obj=None):
#         self.time = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
#         if time_obj is None:
#             pass
#         elif isinstance(time_obj, datetime.datetime):
#             self.time = time_obj
#         else:
#             raise TypeError("Expected datetime.datetime object")
#
#     def to_json(self):
#         if self.is_zero():
#             return '""'
#         return json.dumps(self.time.strftime("%Y-%m-%dT%H:%M:%SZ"))
#
#     def from_json(self, data):
#         if isinstance(data, bytes):
#             data = data.decode("utf-8")
#
#         str_data = data.strip('"')
#         if not str_data:
#             self.time = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
#             return
#
#         try:
#             parsed = datetime.datetime.strptime(str_data, "%Y-%m-%dT%H:%M:%SZ")
#             parsed = parsed.replace(tzinfo=datetime.timezone.utc)
#             self.time = parsed
#         except ValueError as e:
#             raise ValueError(f"Failed to parse RFC3339 date: {e}")
#
#     def is_zero(self):
#         """Check if the time is the zero value"""
#         return self.time == datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
#
#     def __str__(self):
#         """String representation in RFC3339 format"""
#         return self.time.strftime("%Y-%m-%dT%H:%M:%SZ")
def to_rfc339_time(input: Union[str, datetime]) -> datetime:
    if isinstance(input, datetime):
        return input.replace(tzinfo=timezone.utc)
    if isinstance(input, str):
        parsed = datetime.strptime(input, "%Y-%m-%dT%H:%M:%SZ")
        return parsed.replace(tzinfo=timezone.utc)
    raise ValueError("Improper type couldnt be decoded into an RFC3339Time")


def rfctime_serializer(input: datetime) -> str:
    return input.strftime("%Y-%m-%dT%H:%M:%SZ")


RFC3339Time = Annotated[
    datetime, BeforeValidator(to_rfc339_time), PlainSerializer(rfctime_serializer)
]


def is_before(rfctime: RFC3339Time, compare_to: RFC3339Time) -> bool:
    return rfctime <= compare_to


def is_after(rfctime: RFC3339Time, compare_to: RFC3339Time) -> bool:
    return rfctime >= compare_to


def is_between(rfctime: RFC3339Time, start: RFC3339Time, end: RFC3339Time) -> bool:
    return start <= rfctime <= end


def get_beginning_of_year_time(year: int) -> RFC3339Time:
    return date_to_rfctime(date=date(year, 1, 1))


def time_is_in_yearlist(years: List[int], rfctime: RFC3339Time) -> bool:
    if not years:
        return False

    sorted_years = sorted(set(years))
    intervals = []
    current_start = sorted_years[0]
    current_end = current_start + 1

    for year in sorted_years[1:]:
        if year == current_end:
            current_end = year + 1
        else:
            intervals.append((current_start, current_end))
            current_start = year
            current_end = year + 1
    intervals.append((current_start, current_end))

    for start_year, end_year in intervals:
        if is_between(
            rfctime=rfctime,
            start=get_beginning_of_year_time(start_year),
            end=get_beginning_of_year_time(end_year),
        ):
            return True
    return False


def time_is_in_year(year: int, rfctime: RFC3339Time) -> bool:
    return time_is_in_yearlist(years=[year], rfctime=rfctime)


def rfc_time_from_string(input: str) -> RFC3339Time:
    return to_rfc339_time(input)


def rfc_time_now() -> RFC3339Time:
    return datetime.now(tz=timezone.utc)


def rfc_time_from_mmddyyyy(date_str: str) -> RFC3339Time:
    """Create a KesslerTime from a MM/DD/YYYY formatted string"""
    if not date_str:
        raise ValueError("empty date string")

    date_parts = date_str.split("/")
    if len(date_parts) != 3:
        raise ValueError("date string must be in the format MM/DD/YYYY")

    month, day, year = date_parts

    try:
        parsed_date = datetime.strptime(f"{month}/{day}/{year}", "%m/%d/%Y")
        parsed_date = parsed_date.replace(tzinfo=timezone.utc)
        return parsed_date
    except ValueError as e:
        raise ValueError(f"Failed to parse date: {e}")


def date_to_rfctime(date: date) -> RFC3339Time:
    return datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc)


def rfc_time_to_timestamp(rfctime: RFC3339Time) -> float:
    return datetime.timestamp(rfctime)


def rfc_time_from_timestamp(timestamp: float) -> RFC3339Time:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)
