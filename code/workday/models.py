import logging

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class Signing(models.Model):
    start_date = models.DateTimeField('Start working day', default=timezone.now)
    end_date = models.DateTimeField('End working day', blank=True, null=True)
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    description = models.TextField('Signing description', default='')

    def validate_unique(self, *args, **kwargs):
        logger.debug('validate_unique (models.py)')
        if self.end_date and self.start_date > self.end_date:
            raise ValidationError('Invalid time interval for Signing (%(signing)s)',
                                  params={'signing': self.get_humanized_signing()},)

    def get_humanized_signing(self):
        logger.debug('get_humanized_signing (models.py)')
        end = self.end_date.strftime('%H:%M)') if self.end_date else 'Not ended)'
        return self.start_date.strftime('%d %b %Y (%H:%M') + ' - ' + end

    def get_sign_duration(self):
        logger.debug('get_sign_duration (models.py)')
        if self.end_date:
            return self.end_date.replace(microsecond=0) - self.start_date.replace(microsecond=0)
        return timezone.now().replace(microsecond=0) - self.start_date.replace(microsecond=0)

    def __str__(self):
        return self.get_humanized_signing()
