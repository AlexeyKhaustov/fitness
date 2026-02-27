from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from fitness_app.core.models import Document, DocumentVersion, UserConsent  # используйте правильный импорт

class Command(BaseCommand):
    help = 'Создаёт начальные версии документов и согласия для всех пользователей'

    def handle(self, *args, **options):
        # Создаём документы, если их нет
        for doc_type, label in Document.TYPE_CHOICES:
            doc, created = Document.objects.get_or_create(type=doc_type)
            if created:
                self.stdout.write(f'Создан документ {label}')

        # Для каждого документа создаём версию 1 (если нет версий)
        for doc in Document.objects.all():
            if not doc.versions.exists():
                # Определяем номер версии (для первого раза = 1)
                version_number = 1
                version = DocumentVersion.objects.create(
                    document=doc,
                    version_number=version_number,
                    text=f'Текст {doc.get_type_display()} по умолчанию. Замените на реальный.',
                    is_active=True
                )
                doc.current_version = version
                doc.save()
                self.stdout.write(f'Создана версия 1 для {doc.get_type_display()}')
            else:
                # Если версии уже есть, ничего не делаем (можно проверить активную)
                pass

        # Создаём согласия для всех существующих пользователей на текущие активные версии
        active_versions = DocumentVersion.objects.filter(is_active=True)
        for user in User.objects.all():
            for version in active_versions:
                UserConsent.objects.get_or_create(
                    user=user,
                    document_version=version,
                    defaults={
                        'ip_address': '0.0.0.0',
                        'user_agent': 'Initial migration'
                    }
                )
            self.stdout.write(f'Согласия для пользователя {user.username} созданы')