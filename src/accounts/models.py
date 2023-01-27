import pytz
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

TIMEZONE_CHOICES = zip(pytz.all_timezones, pytz.all_timezones)


class Company(models.Model):
    name = models.CharField('Company name', max_length=200)
    description = models.TextField('Company description', blank=True)

    class Meta:
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name


class WorkLocation(models.Model):
    name = models.CharField('Work Location name', max_length=100)
    remote = models.BooleanField('Remote location', default=False)
    latitude = models.FloatField('Location latitude', default=0.0)
    longitude = models.FloatField('Location longitude', default=0.0)

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    laboral_hours = models.FloatField('User working hours per week', default=40)
    timezone = models.CharField('User Timezone', max_length=40, choices=TIMEZONE_CHOICES, default='UTC')
    companies = models.ManyToManyField(Company)
    default_company = models.ForeignKey(Company, on_delete=models.SET_NULL, related_name='default_company', null=True)
    worklocations = models.ManyToManyField(WorkLocation, related_name='user_worklocations', blank=True)

    def __str__(self):
        return self.username
