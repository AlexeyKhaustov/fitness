from django.urls import path
# from . import views

from .views import (
    home,
    profile,
    video_list,
    category_detail,
    VideoDetailView,
)


urlpatterns = [
    path('', home, name='home'),
    path('profile/', profile, name='profile'),
    path('videos/', video_list, name='videos'),
    path('category/<slug:slug>/', category_detail, name='category_detail'),
    # path('video/<int:video_id>/', views.video_detail, name='video_detail'),
    path('video/<int:video_id>/', VideoDetailView.as_view(), name='video_detail'),
]


# from django.urls import path
# from .views import (
#     HomeView,
#     ProfileView,
#     CategoryDetailView,
#     VideoDetailView,
# )
#
# urlpatterns = [
#     path('', HomeView.as_view(), name='home'),
#     path('profile/', ProfileView.as_view(), name='profile'),
#     path('category/<slug:slug>/', CategoryDetailView.as_view(), name='category_detail'),
#     path('video/<int:video_id>/', VideoDetailView.as_view(), name='video_detail'),
# ]