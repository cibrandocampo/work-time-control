import logging

from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth import authenticate
from django.contrib.auth import login as do_login
from django.contrib.auth import logout as do_logout

logger = logging.getLogger(__name__)


def login(request):
    logger.info('login (views.py)')
    context = {'username': '', 'next_page': request.GET.get('next')}
    if request.method == "POST":
        logger.debug('login (views.py): POST')
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_page = request.POST.get('next_page')
        user = authenticate(username=username, password=password)
        if user is not None:
            logger.debug('login (views.py): Logged for: ' + str(username))
            do_login(request, user)
            return redirect('/' if next_page == "None" else next_page)
        logger.warning('login (views.py): Error login for: ' + str(username))
        context = {'username': username, 'next_page': next_page, 'error': True}
    return render(request, 'login.html', context)


def logout(request):
    logger.info('logout (views.py)')
    do_logout(request)
    return redirect('/')
