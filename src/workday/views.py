import csv
import pytz
import logging
import datetime

from .tools import str_to_datetime, get_week_days
from .signings import set_singin, set_singout, get_signings, get_incomplete_signing, get_worked_time

from django.utils import timezone
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt


logger = logging.getLogger(__name__)


@login_required
def signing(request):
    logger.info('signing (views.py)')

    context = {}    
    if request.method == 'POST':
        logger.debug('signing (views.py): POST with action: ' + str(request.POST.get('action')))
        if request.POST.get('action') == 'start':
            set_singin(
                employee=request.user,
                id_company=request.POST.get('company', None),
                id_worklocation=request.POST.get('worklocation', None),
                description=request.POST.get('description', '')
            )

        elif request.POST.get('action') == 'end':
            set_singout(
                employee=request.user, 
                description=request.POST.get('description', '')
            )

    now = timezone.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    context['datetime'] = now
    context['companies'] = request.user.companies.all()
    context['worklocations'] = request.user.worklocations.all()
    context['default_company'] = request.user.default_company
    context['signings'] = get_signings(request.user, today, now)
    context['incomplete_sign'] = get_incomplete_signing(request.user)
    context['worked_time'] = get_worked_time(request.user, context['signings'])
    return render(request, 'signing.html', context)


@csrf_exempt
@login_required
def get_worklocation(request):
    if request.method == 'POST':
        logger.info('get_worklocation (views.py)')
        latitude = request.POST.get('latitude', None)
        longitude = request.POST.get('longitude', None)
        if latitude and longitude:
            near_worklocation = {
                'worklocation_id': 0,
            }
            
            for worklocation in request.user.worklocations.all():
                diff_coord = abs(worklocation.latitude - float(latitude))
                diff_coord += abs(worklocation.longitude - float(longitude))
                if diff_coord > 0.2:
                    continue
                if not near_worklocation['worklocation_id'] or near_worklocation['diff_coord'] > diff_coord:
                    near_worklocation = {
                        'worklocation_id': worklocation.id,
                        'diff_coord': diff_coord
                    }
            
            return JsonResponse(near_worklocation)
 


@login_required
def summary(request):
    logger.info('summary (views.py)')
    context = {}
    if request.method == 'POST':
        logger.debug('summary (views.py): POST')
        context['search_company'] = request.POST.get('company')
        end_day = datetime.timedelta(hours=23, minutes=59, seconds=59)
        context['start_date'] = str_to_datetime(request.POST.get('start_date'))
        context['end_date'] = str_to_datetime(request.POST.get('end_date')) + end_day

    else:
        context['search_company'] = 'all'
        logger.debug('summary (views.py): GET')
        context['start_date'], context['end_date'] = get_week_days()

    context['companies'] = request.user.companies.all()
    context['signings'] = get_signings(request.user, context['start_date'], context['end_date'], context['search_company'])
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
        tz = pytz.timezone(request.user.timezone)
        writer.writerow(['Company', 'Date', 'Remote', 'Start', 'End', 'Worked', 'Description'])
        for sign in get_signings(request.user, start_date, end_date):
            writer.writerow([sign.company if sign.company else '-',
                             sign.start_date.strftime('%d/%m/%Y'),
                             sign.worklocation.remote if sign.worklocation else '-',
                             sign.start_date.astimezone(tz).strftime('%H:%M:%S'),
                             sign.end_date.astimezone(tz).strftime('%H:%M:%S'),
                             sign.get_sign_duration(),
                             sign.description]
                            )
        return response

    logger.debug('export_signings (views.py): GET')
    context = {}
    context['start_date'], context['end_date'] = get_week_days()
    return render(request, 'export.html', context)
