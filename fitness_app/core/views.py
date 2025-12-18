from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import UserProfile, Video, Category

def home(request):
    categories = Category.objects.all()
    latest_videos = Video.objects.filter(is_free=False).order_by('-id')[:12]
    return render(request, 'core/home.html', {
        'categories': categories,
        'latest_videos': latest_videos,
    })

@login_required
def profile(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'core/profile.html', {'user_profile': user_profile})

@login_required
def video_list(request):
    user_profile = UserProfile.objects.get(user=request.user)
    if user_profile.subscription_active:
        videos = Video.objects.all()  # Платные и бесплатные для подписчиков
    else:
        videos = Video.objects.filter(is_free=True)  # Только бесплатные
    return render(request, 'core/video_list.html', {'videos': videos})


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    return render(request, 'core/category_detail.html', {'category': category})

