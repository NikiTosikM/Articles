from datetime import datetime, timedelta


def date_format():
    date: datetime = datetime.now() - timedelta(days=1)
    date_str_format = date.strftime("%Y-%m-%d")

    return date_str_format


def datetime_format(date):
    date_published: datetime = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
    return date_published
    
