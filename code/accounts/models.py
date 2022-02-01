import pytz
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

TIMEZONE_CHOICES = zip(pytz.all_timezones, pytz.all_timezones)


class Company(models.Model):
    name = models.CharField('Company name', max_length=200)
    description = models.TextField('Company description', blank=True)

    class Meta:
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    laboral_hours = models.FloatField('User working hours per week', default=40)
    timezone = models.CharField('User Timezone', max_length=40, choices=TIMEZONE_CHOICES, default='UTC')
    companies = models.ManyToManyField(Company)
    default_company = models.ForeignKey(Company, on_delete=models.SET_NULL, related_name='default_company', null=True)

    def __str__(self):
        return self.username
