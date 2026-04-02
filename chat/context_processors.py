from .models import ChatRoom
from fitness_app.core.models import MarathonAccess

def user_chat_rooms(request):
    if not request.user.is_authenticated:
        return {}
    rooms = []

    # Общий чат
    try:
        general = ChatRoom.objects.get(room_type='general', is_active=True)
        rooms.append({'name': general.name, 'slug': general.slug, 'type': 'general'})
    except ChatRoom.DoesNotExist:
        pass

    # Чаты купленных марафонов
    accesses = MarathonAccess.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('marathon')

    for access in accesses:
        if hasattr(access.marathon, 'chat_room') and access.marathon.chat_room.is_active:
            room = access.marathon.chat_room
            rooms.append({'name': room.name, 'slug': room.slug, 'type': 'marathon'})

    rooms.sort(key=lambda x: x['name'])
    return {'chat_rooms': rooms}