import pytz
import logging
import datetime

from django.utils import timezone

logger = logging.getLogger(__name__)


def str_to_datetime(date, pattern='%Y-%m-%d'):
    logger.debug('str_to_datetime (tools.py): ' + str(date) + ' pattern: ' + str(pattern))
    try:
        return pytz.utc.localize(datetime.datetime.strptime(date, pattern))
    except Exception as e:
        logger.warning('str_to_datetime (tools.py): ' + str(date) + ' pattern: ' + str(pattern) + ' error: ' + str(e))
        return False


def get_week_days():
    logger.debug('get_week_days (tools.py)')
    now = timezone.now().replace(microsecond=0)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = today + datetime.timedelta(days=-today.weekday())
    logger.debug('get_week_days (tools.py): start: ' + str(start_date) + ' end: ' + str(now))
    return [start_date, now]
