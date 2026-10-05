from datetime import datetime

from app.config.settings import settings


def parse_config_date(date_string: str) -> datetime:
    return datetime.strptime(date_string, "%Y-%m-%d")


def is_valid_date(published_date: datetime) -> bool:
    """
    Check whether an article falls inside the assignment date window.
    """

    if published_date is None:
        return False

    start_date = parse_config_date(settings.START_DATE)
    end_date = parse_config_date(settings.END_DATE)

    return start_date <= published_date <= end_date