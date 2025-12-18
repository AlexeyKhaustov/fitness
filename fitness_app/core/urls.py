from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('profile/', views.profile, name='profile'),
    path('videos/', views.video_list, name='videos'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
]
