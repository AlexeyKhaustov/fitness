# Техническая документация: система согласий и версионирования документов

## 1. Модели данных

Все модели находятся в приложении `core` (оригинальные) и для удобства отображения в админке используются прокси-модели в приложении `legal`.

### 1.1. `Document`

| Поле | Тип | Описание |
|------|-----|----------|
| `type` | CharField(choices) | Тип документа (`privacy`, `terms`, `offer`) |
| `current_version` | ForeignKey(DocumentVersion) | Текущая активная версия |

### 1.2. `DocumentVersion`

| Поле | Тип | Описание |
|------|-----|----------|
| `document` | ForeignKey(Document) | Связанный документ |
| `version_number` | PositiveIntegerField | Номер версии (уникален в рамках документа) |
| `created_at` | DateTimeField | Дата создания версии |
| `content_hash` | CharField(sha256) | Хеш текста (для отслеживания изменений) |
| `text` | TextField | Полный текст документа |
| `is_active` | BooleanField | Активна ли данная версия |

### 1.3. `UserConsent`

| Поле | Тип | Описание |
|------|-----|----------|
| `user` | ForeignKey(User) | Пользователь |
| `document_version` | ForeignKey(DocumentVersion) | Версия документа, на которую дано согласие |
| `consented_at` | DateTimeField | Дата и время согласия |
| `ip_address` | GenericIPAddressField | IP-адрес пользователя в момент согласия |
| `user_agent` | TextField | User-Agent браузера |

Уникальное ограничение: `(user, document_version)` — пользователь может дать согласие на каждую версию только один раз.

## 2. Middleware: `ConsentMiddleware`

Расположение: `core/middleware.py`

**Назначение:** проверять для аутентифицированных пользователей, есть ли у них согласие на все активные версии документов.

**Логика:**
- Список исключённых путей: `/accept-consent/`, `/accounts/logout/`, `/admin/`, `/static/`, `/media/`.
- Если текущий путь не входит в исключения, вызывается `has_valid_consents(user)`.
- Если согласий не хватает, в сессию сохраняется исходный URL (`next_url`) и происходит редирект на `accept_consent`.

```python
def has_valid_consents(self, user):
    active_versions = DocumentVersion.objects.filter(is_active=True)
    consented_ids = UserConsent.objects.filter(
        user=user,
        document_version__in=active_versions
    ).values_list('document_version_id', flat=True)
    return set(active_versions.values_list('id', flat=True)) == set(consented_ids)
```

3. Представление accept_consent

Путь: /accept-consent/ (имя accept_consent)

GET-запрос:

    Получает все активные версии, на которые у пользователя нет согласия.

    Если таких нет — редирект на next_url (или главную).

    Рендерит шаблон со списком документов (каждый с полным текстом новой версии).

POST-запрос:

    action=accept: для каждой ожидающей версии создаётся запись UserConsent. Флаг restricted_access (если был) удаляется из сессии. Редирект на next_url.

    action=reject: проверяется наличие активных покупок (модели MarathonAccess, UserSubscription). Если они есть — в сессию устанавливается restricted_access = True и пользователь перенаправляется в профиль. Если нет — пользователь разлогинивается.

4. Декоратор full_access_required

Расположение: core/decorators.py

Назначение: ограничивать доступ к view, требующим полного согласия (покупка, заявки, комментарии).

```python

def full_access_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.session.get('restricted_access'):
            messages.error(request, 'Для выполнения этого действия необходимо принять обновлённые условия.')
            return redirect('accept_consent')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
```

Используется, например, в marathon_purchase, service_request_submit, add_video_comment.
5. Интеграция с регистрацией

В кастомной форме CustomSignupForm добавлено поле terms_accepted (BooleanField, required=True). После сохранения пользователя (save) для всех активных версий создаются записи UserConsent с IP и User-Agent из запроса.
6. Администрирование документов
6.1. Кастомные URL для экшенов

В корневом urls.py добавлены пути перед admin.site.urls:

```python

path('admin/create-document-version/<int:doc_id>/', staff_member_required(admin_views.create_document_version), name='create_document_version'),
path('admin/set-active-version/<int:version_id>/', staff_member_required(admin_views.set_active_version), name='set_active_version'),
```

Это необходимо, чтобы стандартный обработчик админки не перехватывал эти запросы.
6.2. Функции в admin_views.py

    create_document_version(doc_id) — создаёт новую версию документа, увеличивая номер, копирует текст из текущей версии (если есть).

    set_active_version(version_id) — делает указанную версию активной, деактивируя все остальные версии этого документа, и обновляет current_version в документе.

7. Команда инициализации

python manage.py init_documents (лежит в core/management/commands/init_documents.py):

    Создаёт три документа, если их нет.

    Для каждого создаёт версию 1 с текстом-заглушкой и делает её активной.

    Для всех существующих пользователей создаёт согласия на эти версии (с заглушками IP и User-Agent).

Запускается один раз после добавления системы согласий.
8. Шаблоны

    core/accept_consent.html — страница принятия новых условий.

    В base.html добавлено уведомление для пользователей с restricted_access (жёлтая плашка).

    В подвале добавлены ссылки на страницы документов (/doc/<type>/), которые отображают текущую версию.

9. Важные моменты

    Все новые миграции применяются стандартно через makemigrations и migrate.

    При изменении текста документа администратор обязан создать новую версию и активировать её, иначе изменения не вступят в силу для пользователей.

    Middleware проверяет согласия только для аутентифицированных пользователей. Анонимные пользователи видят только публичную часть.

