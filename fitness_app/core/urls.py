from django.urls import path
from . import views

urlpatterns = [
    # Основные страницы
    path('', views.home, name='home'),
    path('profile/', views.profile, name='profile'),

    # Категории
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),

    # Видео (обычные)
    path('video/<int:video_id>/', views.VideoDetailView.as_view(), name='video_detail'),
    path('video/<int:video_id>/comment/', views.add_video_comment, name='add_video_comment'),
    path('video/<int:video_id>/like/', views.toggle_video_like, name='toggle_video_like'),

    # Марафоны
    path('marathons/', views.marathon_list, name='marathon_list'),
    path('marathon/<slug:slug>/', views.marathon_detail, name='marathon_detail'),
    path('marathon/<slug:marathon_slug>/video/<int:video_id>/',
         views.marathon_video_detail, name='marathon_video_detail'),
    path('marathon/<slug:slug>/purchase/', views.marathon_purchase, name='marathon_purchase'),
    path('my-marathons/', views.my_marathons, name='my_marathons'),

    # Внутренние страницы
    path('videos/', views.video_list, name='videos'),
]
#
# from django.urls import path
# from .views import (
#     home,
#     profile,
#     video_list,
#     category_detail,
#     VideoDetailView,
#     marathon_list,
#     marathon_detail,
#     marathon_purchase,
#     my_marathons,
# )
#
# urlpatterns = [
#     path('', home, name='home'),
#     path('profile/', profile, name='profile'),
#     path('videos/', video_list, name='videos'),
#     path('category/<slug:slug>/', category_detail, name='category_detail'),
#     path('video/<int:video_id>/', VideoDetailView.as_view(), name='video_detail'),
#
#     # Марафоны
#     path('marathons/', marathon_list, name='marathon_list'),
#     path('marathon/<slug:slug>/', marathon_detail, name='marathon_detail'),
#     path('marathon/<slug:slug>/purchase/', marathon_purchase, name='marathon_purchase'),
#     path('my-marathons/', my_marathons, name='my_marathons'),
# ]