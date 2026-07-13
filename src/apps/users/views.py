from django.contrib.auth import login
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _

from .forms import RegisterForm
from .models import Profile, ROLE_ENTREPRENEUR


def _role_home(user):
    """Where a user lands after auth, based on role."""
    try:
        if user.profile.is_entrepreneur:
            return reverse('dashboard:readiness')
    except Profile.DoesNotExist:
        pass
    return reverse('dashboard:index')


def register(request):
    if request.user.is_authenticated:
        return redirect(_role_home(request.user))

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, _('Welcome to NovdAI!'))
            return redirect(_role_home(user))
    else:
        form = RegisterForm()

    return render(request, 'users/register.html', {'form': form})


def post_login_redirect(request):
    """LOGIN_REDIRECT_URL target — branch by role."""
    if request.user.is_authenticated:
        return redirect(_role_home(request.user))
    return redirect('users:login')
