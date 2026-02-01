import os
from pathlib import Path
from decouple import config
from django.contrib.messages import constants as messages

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Безопасность
SECRET_KEY = config('DJANGO_SECRET_KEY')
DEBUG = config('DJANGO_DEBUG', default=True, cast=bool)

# ALLOWED_HOSTS берется из переменной окружения
ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

MESSAGE_TAGS = {
    messages.SUCCESS: 'success',
    messages.ERROR: 'error',
    messages.WARNING: 'warning',
    messages.INFO: 'info',
}

# Добавляем доверенные источники для CSRF (обязательно при работе через nginx на порту 8080)
CSRF_TRUSTED_ORIGINS = []

for host in ALLOWED_HOSTS:
    if host and host != '*':
        clean_host = host.split(':')[0] if ':' in host else host

        # Основные
        CSRF_TRUSTED_ORIGINS.append(f'https://{clean_host}')
        CSRF_TRUSTED_ORIGINS.append(f'http://{clean_host}')

        # Порт 8080
        CSRF_TRUSTED_ORIGINS.append(f'http://{clean_host}:8080')
        CSRF_TRUSTED_ORIGINS.append(f'https://{clean_host}:8080')

if DEBUG:
    CSRF_TRUSTED_ORIGINS.extend([
        'http://localhost:8000',
        'http://localhost:8080',
        'http://127.0.0.1:8000',
        'http://127.0.0.1:8080',
    ])

CSRF_TRUSTED_ORIGINS = list(set(CSRF_TRUSTED_ORIGINS))

# Приложения
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'rest_framework',
    'fitness_app.core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'fitness_app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'fitness_app.core.context_processors.active_banners',
                'fitness_app.core.context_processors.active_seo_blocks',
                'fitness_app.core.context_processors.marathon_stats',
                'fitness_app.core.context_processors.user_marathon_access',
                'fitness_app.core.context_processors.categories_processor',
            ],
        },
    },
]

ACCOUNT_FORMS = {
    'signup': 'fitness_app.core.forms.CustomSignupForm',
    'login': 'fitness_app.core.forms.CustomLoginForm',
}

WSGI_APPLICATION = 'fitness_app.wsgi.application'

# База данных - ИСПРАВЛЕНО: используем POSTGRES_* переменные из .env
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB', default='fitness_db'),
        'USER': config('POSTGRES_USER', default='fitness_user'),
        'PASSWORD': config('POSTGRES_PASSWORD', default=''),
        'HOST': config('POSTGRES_HOST', default='db'),
        'PORT': config('POSTGRES_PORT', default=5432),
    }
}

# Валидация паролей
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Интернационализация
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Статические и медиафайлы
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Allauth настройки
SITE_ID = 1
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]
ACCOUNT_LOGIN_METHODS = ['email', 'username']
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_LOGIN_REDIRECT_URL = '/profile/'
ACCOUNT_SIGNUP_REDIRECT_URL = '/profile/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/'
LOGIN_REDIRECT_URL = '/profile/'

ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_EMAIL_REQUIRED = False


# Безопасность
# Важно: Django за обратным прокси с SSL
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Настройки безопасности в зависимости от DEBUG
if not DEBUG:
    # ПРОДАКШЕН: Nginx уже обработал SSL, не перенаправляем
    SECURE_SSL_REDIRECT = False
    
    # Куки должны быть защищены (браузер использует HTTPS)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # Другие security настройки
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
else:
    # РАЗРАБОТКА: отключаем HTTPS требования
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# Отладка CSRF кук (для разработки)
CSRF_COOKIE_HTTPONLY = False
