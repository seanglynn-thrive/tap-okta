"""Util functions."""
from datetime import datetime
import logging

TS_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

logger = logging.getLogger("tap_okta_utils")


def validate_datetime(datetime_val: datetime, datetime_format: str = TS_FORMAT):
    """Validate a datetime object is in expected format. Default: (%Y-%m-%dT%H:%M:%SZ)."""
    try:
        datetime_str = datetime_val.strftime(TS_FORMAT)
        logger.debug(
            f"Validating TS: {datetime_str} conforms to format: {datetime_format}"
        )
        datetime.strptime(datetime_str, datetime_format)
    except ValueError:
        raise ValueError(
            f"Incorrect datetime format, {datetime_val} should be {datetime_format}"
        )


def reformat_datetime(
    datetime_val: datetime,
    old_format: str = "%Y-%m-%dT%H:%M:%S",
    new_format: str = TS_FORMAT,
) -> str:
    """Get reformatted str datetime. Default: (%Y-%m-%dT%H:%M:%SZ)."""
    datetime_str = datetime_val.strftime(TS_FORMAT)
    logger.debug(f"Converting '{datetime_str}' from '{old_format}' -> '{new_format}'.")
    datetime_object = datetime.strptime(datetime_str, old_format)
    new_datetime = datetime_object.strftime(new_format)

    return new_datetime
