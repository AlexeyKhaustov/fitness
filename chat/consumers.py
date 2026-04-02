import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User

from .models import ChatRoom, ChatMessage
from fitness_app.core.models import MarathonAccess

class ChatConsumer(AsyncWebsocketConsumer):
    room_slug: str
    user: User
    room: ChatRoom
    room_group_name: str

    async def connect(self):
        self.room_slug = self.scope['url_route']['kwargs']['room_slug']
        self.user = self.scope['user']

        if self.user.is_anonymous:
            await self.close()
            return

        self.room = await self.get_room(self.room_slug) # noqa
        if not self.room:
            await self.close()
            return

        if not await self.check_access(): # noqa
            await self.close()
            return

        self.room_group_name = f'chat_{self.room.id}' # noqa

        # Принимаем соединение один раз
        await self.accept()

        # Добавляем канал в группу
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        # Отправляем историю
        await self.send_history()

    async def send_history(self):
        """Отправляет последние n сообщений одной порцией."""
        messages = await self.get_last_messages(limit=50) # noqa
        await self.send(text_data=json.dumps({
            'type': 'history',
            'messages': [
                {
                    'id': msg.id,
                    'text': msg.text,
                    'username': msg.user.username,
                    'user_id': msg.user.id,
                    'created_at': msg.created_at.isoformat(),
                }
                for msg in messages
            ]
        }))

    @database_sync_to_async
    def get_last_messages(self, limit=50):
        # Возвращаем список сообщений в хронологическом порядке (старые внизу)
        qs = self.room.messages.select_related('user').order_by('-created_at')[:limit] # noqa
        return list(reversed(qs))   # переворачиваем, чтобы старые были первыми

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            data = json.loads(text_data)
            message_text = data.get('message', '').strip()
            if not message_text:
                return

            message = await self.save_message(message_text) # noqa

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'id': message.id,
                        'text': message.text,
                        'username': self.user.username,
                        'user_id': self.user.id, # noqa
                        'created_at': message.created_at.isoformat(),
                    }
                }
            )
        elif bytes_data:
            # Если нужно поддержать бинарные сообщения (картинки и т.д.)
            pass

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event['message']))

    @database_sync_to_async
    def get_room(self, slug):
        try:
            return ChatRoom.objects.get(slug=slug, is_active=True)
        except ChatRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def check_access(self):
        if self.room.room_type == 'general':
            return True
        elif self.room.room_type == 'marathon' and self.room.marathon:
            return MarathonAccess.objects.filter(
                user=self.user,
                marathon=self.room.marathon,
                is_active=True
            ).exists()
        return False

    @database_sync_to_async
    def save_message(self, text):
        return ChatMessage.objects.create(
            room=self.room,
            user=self.user,
            text=text
        )