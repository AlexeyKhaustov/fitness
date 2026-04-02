from django.urls import path
from . import views

urlpatterns = [
    path('<slug:room_slug>/', views.chat_room, name='chat_room'),
]