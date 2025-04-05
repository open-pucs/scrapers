import datetime
import json


class RFC3339Time:

    def __init__(self, time_obj=None):
        self.time = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
        if time_obj is None:
            pass
        elif isinstance(time_obj, datetime.datetime):
            self.time = time_obj
        else:
            raise TypeError("Expected datetime.datetime object")

    def to_json(self):
        if self.is_zero():
            return '""'
        return json.dumps(self.time.strftime("%Y-%m-%dT%H:%M:%SZ"))

    def from_json(self, data):
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        str_data = data.strip('"')
        if not str_data:
            self.time = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
            return

        try:
            parsed = datetime.datetime.strptime(str_data, "%Y-%m-%dT%H:%M:%SZ")
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
            self.time = parsed
        except ValueError as e:
            raise ValueError(f"Failed to parse RFC3339 date: {e}")

    def is_zero(self):
        """Check if the time is the zero value"""
        return self.time == datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)

    def __str__(self):
        """String representation in RFC3339 format"""
        return self.time.strftime("%Y-%m-%dT%H:%M:%SZ")


def rfc_time_now() -> RFC3339Time:
    return RFC3339Time(datetime.datetime.now(tz=datetime.timezone.utc))


def rfc_time_from_string(str_data: str) -> RFC3339Time:
    """Create a KesslerTime from a string"""
    kt = RFC3339Time()
    kt.from_json(f'"{str_data}"')
    return kt


def rfc_time_from_mmddyyyy(date_str: str) -> RFC3339Time:
    """Create a KesslerTime from a MM/DD/YYYY formatted string"""
    if not date_str:
        raise ValueError("empty date string")

    date_parts = date_str.split("/")
    if len(date_parts) != 3:
        raise ValueError("date string must be in the format MM/DD/YYYY")

    month, day, year = date_parts

    try:
        parsed_date = datetime.datetime.strptime(f"{month}/{day}/{year}", "%m/%d/%Y")
        parsed_date = parsed_date.replace(tzinfo=datetime.timezone.utc)
        return RFC3339Time(parsed_date)
    except ValueError as e:
        raise ValueError(f"Failed to parse date: {e}")
