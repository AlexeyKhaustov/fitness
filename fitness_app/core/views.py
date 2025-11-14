from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import UserProfile

def home(request):
    return render(request, 'core/home.html')

@login_required
def profile(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'core/profile.html', {'user_profile': user_profile})