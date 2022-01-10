import logging
import datetime

from .models import Signing

from django.utils import timezone

logger = logging.getLogger(__name__)


def get_signings(employee, start_date, end_date):
    logger.debug('get_signings (signings.py): ' + str(employee) + ' dates: ' + str(start_date) + '/' + str(end_date))
    signs = Signing.objects.filter(employee=employee).filter(start_date__gt=start_date).filter(start_date__lt=end_date)
    logger.debug('get_signings (signings.py): Signs ' + str(signs))
    return signs.order_by('start_date')


def get_incomplete_signing(employee):
    logger.debug('get_incomplete_signing (signings.py): employee ' + str(employee))
    return Signing.objects.filter(employee=employee).filter(end_date=None).first()


def get_worked_time(employee, signings):
    logger.debug('get_worked_time (signings.py): employee ' + str(employee) + ' signings: ' + str(signings))
    worked_time = datetime.timedelta(0)
    for sign in signings:
        worked_time += sign.get_sign_duration()
    logger.debug('get_worked_time (signings.py): worked time: ' + str(worked_time))
    return worked_time


def set_singin(employee):
    logger.debug('set_singin (signings.py): employee ' + str(employee))
    if get_incomplete_signing(employee):
        logger.warning('set_singin (signings.py): Incomplete signing, singout before signin - ' + str(employee))
        set_singout(employee)
        return False
    new_signing = Signing(employee=employee)
    new_signing.save()
    logger.debug('set_singin (signings.py): completed! ')
    return new_signing


def set_singout(employee, description):
    logger.debug('set_singout (signings.py): employee ' + str(employee))
    signing = get_incomplete_signing(employee)
    if signing:
        signing.end_date = timezone.now().replace(microsecond=0)
        signing.description = description
        signing.save()
        logger.debug('set_singout (signings.py): completed! ')
        return True
    logger.warning('set_singout (signings.py): Invalid signing - ' + str(employee))
    return False
