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
    path('comment/<int:comment_id>/json/', views.get_comment_json, name='comment_json'),

    # Марафоны
    path('marathons/', views.marathon_list, name='marathon_list'),
    path('marathon/<slug:slug>/', views.marathon_detail, name='marathon_detail'),
    path('marathon/<slug:marathon_slug>/video/<int:video_id>/',
         views.marathon_video_detail, name='marathon_video_detail'),
    path('marathon/<slug:slug>/purchase/', views.marathon_purchase, name='marathon_purchase'),
    path('my-marathons/', views.my_marathons, name='my_marathons'),

    # Внутренние страницы
    path('videos/', views.video_list, name='videos'),

    # Услуги
    path('services/<slug:slug>/', views.service_detail, name='service_detail'),
    path('services/<slug:slug>/request/', views.service_request_submit, name='service_request_submit'),

    # Мои заявки
    path('my-services/', views.my_service_requests, name='my_service_requests'),

    # Редактирование профиля
    path('profile/edit/', views.edit_profile, name='edit_profile'),
]
