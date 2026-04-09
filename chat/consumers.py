import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import ChatRoom, ChatMessage
from fitness_app.core.models import MarathonAccess

class ChatConsumer(AsyncWebsocketConsumer):
    """
    Асинхронный WebSocket consumer для обработки чат-сообщений.
    Поддерживает:
    - историю сообщений при подключении (последние 50)
    - отправку новых сообщений в группу комнаты
    - ping/pong heartbeat для поддержания соединения
    - проверку доступа к комнате (общий чат / чат марафона)
    """

    # Атрибуты, которые будут установлены в connect()
    room_slug: str
    user: User
    room: ChatRoom
    room_group_name: str
    limit: int = 50

    async def connect(self):
        """
        Обработчик нового WebSocket-соединения.
        Выполняет:
        1. Извлечение параметров маршрута и пользователя.
        2. Проверку аутентификации.
        3. Получение объекта комнаты и проверку доступа.
        4. Принятие соединения и добавление канала в группу.
        5. Отправку истории сообщений.
        """
        # Получаем slug комнаты из URL
        self.room_slug = self.scope['url_route']['kwargs']['room_slug']
        self.user = self.scope['user']

        # Анонимные пользователи не допускаются
        if self.user.is_anonymous:
            await self.close()
            return

        # Загружаем объект комнаты из БД
        self.room = await self.get_room(self.room_slug)
        if not self.room:
            await self.close()
            return

        # Проверяем, имеет ли пользователь доступ к этой комнате
        if not await self.check_access():
            await self.close()
            return

        # Имя группы в канальном слое (Redis), уникальное для комнаты
        self.room_group_name = f'chat_{self.room.id}'

        # Принимаем WebSocket-соединение
        await self.accept()

        # Добавляем текущий канал в группу, чтобы получать сообщения от других участников
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        # Отправляем последние 50 сообщений новому пользователю
        await self.send_history()

    async def send_history(self):
        """
        Отправляет клиенту историю сообщений (последние 50) в формате JSON.
        Использует тип 'history', чтобы клиент мог отличить историю от живых сообщений.
        """
        messages = await self.get_last_messages(limit=self.limit)
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
    def get_last_messages(self, limit=limit):
        """
        Синхронный метод, выполняемый в отдельном потоке (database_sync_to_async).
        Возвращает список последних сообщений в хронологическом порядке (старые сверху).
        """
        # Берём последние limit сообщений, отсортированных по убыванию даты
        qs = self.room.messages.select_related('user').order_by('-created_at')[:limit]
        # Переворачиваем, чтобы старые сообщения были в начале (для правильного порядка)
        return list(reversed(qs))

    async def disconnect(self, close_code):
        """
        Вызывается при закрытии WebSocket-соединения.
        Удаляет канал из группы комнаты.
        """
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data=None, bytes_data=None):
        """
        Обработчик входящих сообщений от клиента.
        Поддерживает:
        - текстовые сообщения (JSON)
        - команду ping (heartbeat)
        - бинарные данные (опционально)
        """
        if text_data:
            data = json.loads(text_data)

            # === HEARTBEAT: обработка ping ===
            # Если клиент отправил {'type': 'ping'}, отвечаем {'type': 'pong'}
            if data.get('type') == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
                return

            # === Обычное сообщение чата ===
            message_text = data.get('message', '').strip()
            if not message_text:
                return  # Игнорируем пустые сообщения

            # Сохраняем сообщение в базе данных
            message = await self.save_message(message_text)

            # Рассылаем сообщение всем участникам группы (включая отправителя)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',    # имя метода, который будет вызван у всех consumer'ов в группе
                    'message': {
                        'id': message.id,
                        'text': message.text,
                        'username': self.user.username,
                        'user_id': self.user.id,
                        'created_at': message.created_at.isoformat(),
                    }
                }
            )
        elif bytes_data:
            # Если в будущем потребуется поддержка бинарных данных (например, изображения)
            # Здесь можно добавить обработку.
            pass

    async def chat_message(self, event):
        """
        Метод, вызываемый при получении события 'chat_message' из группы.
        Просто пересылает сообщение клиенту.
        """
        await self.send(text_data=json.dumps(event['message']))

    # ---------- Вспомогательные методы для работы с БД (синхронные, обёрнутые в database_sync_to_async) ----------
    @database_sync_to_async
    def get_room(self, slug):
        """Возвращает объект ChatRoom по slug или None, если комната не найдена или не активна."""
        try:
            return ChatRoom.objects.get(slug=slug, is_active=True)
        except ChatRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def check_access(self):
        """
        Проверяет, имеет ли пользователь доступ к комнате.
        - Для general-комнаты доступ всегда открыт (если аутентифицирован).
        - Для marathon-комнаты требуется активная подписка (MarathonAccess).
        """
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
        """Создаёт и сохраняет новое сообщение в базе данных."""
        return ChatMessage.objects.create(
            room=self.room,
            user=self.user,
            text=text
        )