from datetime import (
    datetime, 
    date, 
    timezone, 
    timedelta
)

class DateFormatter():
    @staticmethod
    def converting_date_to_string(num_days: int) -> str:
        ''' 
        Сonverts the date into a string for further article search 
        num_days - indicates how many days need to be subtracted from today
        '''
        date_: date = datetime.now(timezone.utc) - timedelta(days=num_days)
        date_str_format = date_.strftime("%Y-%m-%d")

        return date_str_format

    @staticmethod
    def converting_string_to_date(date_: str) -> datetime:
        ''' converts a string to a date '''
        date_published: datetime = datetime.strptime(date_, "%Y-%m-%dT%H:%M:%SZ")

        return date_published
