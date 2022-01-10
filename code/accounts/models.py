import pytz
from django.db import models
from django.contrib.auth.models import AbstractUser


TIMEZONE_CHOICES = zip(pytz.all_timezones, pytz.all_timezones)


class CustomUser(AbstractUser):
    laboral_hours = models.FloatField('User working hours per week', default=40)
    timezone = models.CharField('User Timezone', max_length=40, choices=TIMEZONE_CHOICES, default='UTC')

    def __str__(self):
        return self.username
