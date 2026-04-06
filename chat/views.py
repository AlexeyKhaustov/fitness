from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.core.exceptions import PermissionDenied
from django.views.decorators.cache import never_cache

from .models import ChatRoom
from fitness_app.core.models import MarathonAccess

@never_cache
def chat_room(request, room_slug):
    room = get_object_or_404(ChatRoom, slug=room_slug, is_active=True)

    # Проверка доступа для чатов марафонов
    if room.room_type == 'marathon':
        if not MarathonAccess.objects.filter(
            user=request.user,
            marathon=room.marathon,
            is_active=True
        ).exists():
            raise PermissionDenied

    return render(request, 'chat/room.html', {'room': room})