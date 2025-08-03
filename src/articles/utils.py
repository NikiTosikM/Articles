from datetime import datetime, timedelta, date, timezone


def date_format() -> str:
    date_: date = datetime.now(timezone.utc) - timedelta(days=1)
    date_str_format = date_.strftime("%Y-%m-%d")

    return date_str_format


def datetime_format(date_) -> datetime:
    date_published: datetime = datetime.strptime(date_, "%Y-%m-%dT%H:%M:%SZ")

    return date_published


def decode_keys_and_value(article: dict[bytes, bytes]) -> dict[str, str]:
    result_decode = {key.decode("utf-8"): value.decode("utf-8") for key, value in article.items()}

    return result_decode

def decode_info(info: list[bytes]) -> dict[str, str]:
    fields = ["id", "title", "category", "views"]
    decode_data = {field: info[i].decode("utf-8") for i, field in enumerate(fields)}
    
    return decode_data