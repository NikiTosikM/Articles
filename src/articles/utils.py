from datetime import datetime, timedelta, date, timezone


def date_format() -> str:
    date_: date = datetime.now(timezone.utc) - timedelta(days=1)
    date_str_format = date_.strftime("%Y-%m-%d")

    return date_str_format


def datetime_format(date_) -> datetime:
    date_published: datetime = datetime.strptime(date_, "%Y-%m-%dT%H:%M:%SZ")

    return date_published


def decode_keys_and_value(article: dict[bytes, bytes]) -> dict[str, str]:
    result_decode = {
       k.decode("utf-8"): v.decode("utf-8")
        for k, v in article.items()
    }
    
    return result_decode
