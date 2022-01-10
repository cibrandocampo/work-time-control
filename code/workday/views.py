import csv
import logging
import datetime

from .tools import str_to_datetime, get_week_days
from .signings import set_singin, set_singout, get_signings, get_incomplete_signing, get_worked_time

from django.utils import timezone
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)


@login_required
def signing(request):
    logger.info('signing (views.py)')
    if request.method == 'POST':
        logger.debug('signing (views.py): POST with action: ' + str(request.POST.get('action')))
        if request.POST.get('action') == 'start':
            set_singin(request.user)

        elif request.POST.get('action') == 'end':
            set_singout(request.user, request.POST.get('description'))

    context = {}
    now = timezone.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    context['datetime'] = now
    context['signings'] = get_signings(request.user, today, now)
    context['incomplete_sign'] = get_incomplete_signing(request.user)
    context['worked_time'] = get_worked_time(request.user, context['signings'])
    return render(request, 'signing.html', context)


@login_required
def summary(request):
    logger.info('summary (views.py)')
    context = {}
    if request.method == 'POST':
        logger.debug('summary (views.py): POST')
        end_day = datetime.timedelta(hours=23, minutes=59, seconds=59)
        context['start_date'] = str_to_datetime(request.POST.get('start_date'))
        context['end_date'] = str_to_datetime(request.POST.get('end_date')) + end_day

    else:
        logger.debug('summary (views.py): GET')
        context['start_date'], context['end_date'] = get_week_days()

    context['signings'] = get_signings(request.user, context['start_date'], context['end_date'])
    context['worked_time'] = get_worked_time(request.user, context['signings'])
    return render(request, 'summary.html', context)


@login_required
def export_signings(request):
    logger.info('export_signings (views.py)')
    if request.method == 'POST':
        logger.debug('export_signings (views.py): POST')
        end_day = datetime.timedelta(hours=23, minutes=59, seconds=59)
        start_date = str_to_datetime(request.POST.get('start_date'))
        end_date = str_to_datetime(request.POST.get('end_date')) + end_day

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="signings_' + str(request.user.username) + '".csv"'
        response.write(u'\ufeff'.encode('utf8'))

        writer = csv.writer(response, delimiter=';')
        writer.writerow(['Start date', 'End date', 'Worked interval', 'Description'])
        for sign in get_signings(request.user, start_date, end_date):
            writer.writerow([sign.start_date,
                             sign.end_date,
                             sign.get_sign_duration(),
                             sign.description]
                            )
        return response

    logger.debug('export_signings (views.py): GET')
    context = {}
    context['start_date'], context['end_date'] = get_week_days()
    return render(request, 'export.html', context)
