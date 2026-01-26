from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True)
    subscription_active = models.BooleanField(default=False)

    def __str__(self):
        return self.full_name


class Category(models.Model):
    name = models.CharField('Название', max_length=100)
    slug = models.SlugField('URL', max_length=100, unique=True)
    icon = models.CharField('Иконка (Font Awesome)', max_length=50, default='film',
                            help_text='Например: dumbbell, running, heart-pulse, yoga, fire')
    color = models.CharField('Цвет (Tailwind)', max_length=300, default='bg-gradient-to-br from-purple-600 to-pink-600')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('category_detail', args=[self.slug])


class Video(models.Model):
    title = models.CharField(max_length=100)
    file = models.FileField(upload_to='videos/')
    description = models.TextField()
    is_free = models.BooleanField(default=False)
    categories = models.ManyToManyField(
        Category,
        related_name='videos',
        blank=True,
        verbose_name='Категории'
    )
    # Новые поля с default значениями
    duration = models.IntegerField('Длительность (секунды)', default=0, help_text='Длительность видео в секундах')
    thumbnail = models.ImageField('Превью', upload_to='video_thumbs/', blank=True, null=True)
    created_at = models.DateTimeField('Дата добавления', auto_now_add=True)
    views = models.IntegerField('Просмотры', default=0)

    class Meta:
        verbose_name = 'Видео'
        verbose_name_plural = 'Видео'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('video_detail', args=[str(self.id)])

    def get_duration_display(self):
        """Форматированная длительность (MM:SS)"""
        minutes = self.duration // 60
        seconds = self.duration % 60
        return f"{minutes:02d}:{seconds:02d}"

    def increment_views(self):
        """Увеличить счетчик просмотров"""
        self.views += 1
        self.save(update_fields=['views'])


class Banner(models.Model):
    title = models.CharField('Заголовок', max_length=200)
    subtitle = models.TextField('Подзаголовок', max_length=500, blank=True)
    button_text = models.CharField('Текст кнопки', max_length=50, default='Смотреть')
    button_link = models.CharField('Ссылка кнопки', max_length=200, default='/')
    image = models.ImageField('Изображение', upload_to='banners/')
    image_mobile = models.ImageField('Изображение (мобильное)', upload_to='banners/mobile/', blank=True)

    # Стилизация
    text_color = models.CharField('Цвет текста', max_length=7, default='#FFFFFF')
    overlay_color = models.CharField('Цвет оверлея', max_length=25, default='rgba(0,0,0,0.4)')
    text_position = models.CharField('Позиция текста', max_length=20,
                                     choices=[('left', 'Слева'), ('center', 'Центр'), ('right', 'Справа')],
                                     default='center')

    # Управление
    is_active = models.BooleanField('Активный', default=True)
    priority = models.IntegerField('Приоритет', default=1,
                                   help_text='Чем выше число, тем выше приоритет')
    show_on_mobile = models.BooleanField('Показывать на мобильных', default=True)
    show_on_desktop = models.BooleanField('Показывать на ПК', default=True)

    # Даты
    start_date = models.DateTimeField('Дата начала показа', blank=True, null=True)
    end_date = models.DateTimeField('Дата окончания показа', blank=True, null=True)

    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Баннер'
        verbose_name_plural = 'Баннеры'
        ordering = ['-priority', '-created_at']

    def __str__(self):
        return self.title

    @property
    def is_currently_active(self):
        """Проверяет, активен ли баннер в текущее время"""
        if not self.is_active:
            return False

        now = timezone.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False

        return True


class SeoBlock(models.Model):
    STYLE_CHOICES = [
        ('default', 'По умолчанию (темный градиент)'),
        ('light', 'Светлый фон'),
        ('image_left', 'Изображение слева, текст справа'),
        ('image_right', 'Изображение справа, текст слева'),
        ('centered', 'Центрированный текст без изображения'),
        ('gradient', 'Градиентный фон без изображения'),
    ]

    HEADER_TAG_CHOICES = [
        ('h1', 'H1'),
        ('h2', 'H2'),
        ('h3', 'H3'),
    ]

    title = models.CharField('Заголовок', max_length=200)
    content = models.TextField('Контент',
                               help_text='Можно использовать HTML теги: <strong>, <em>, <a>, <ul>, <li>, <p>')
    slug = models.SlugField('URL-идентификатор', max_length=100, unique=True)

    # Стилизация
    style = models.CharField('Стиль отображения', max_length=20, choices=STYLE_CHOICES, default='default')
    background_color = models.CharField('Цвет фона', max_length=7, default='#1f2937')
    text_color = models.CharField('Цвет текста', max_length=7, default='#ffffff')
    header_tag = models.CharField('Тег заголовка', max_length=2, choices=HEADER_TAG_CHOICES, default='h2')
    image = models.ImageField('Изображение', upload_to='seo_blocks/', blank=True, null=True)

    # Управление
    is_active = models.BooleanField('Активный', default=True)
    order = models.IntegerField('Порядок', default=0, help_text='Чем меньше число, тем выше блок')
    show_on_home = models.BooleanField('Показывать на главной', default=True)
    show_on_category = models.BooleanField('Показывать в категориях', default=False)

    # Даты
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'SEO блок'
        verbose_name_plural = 'SEO блоки'
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title


class SubscriptionPlan(models.Model):
    PERIOD_CHOICES = [
        (1, '1 месяц'),
        (3, '3 месяца'),
        (12, '12 месяцев'),
    ]

    name = models.CharField('Название', max_length=100)
    period = models.IntegerField('Период (месяцы)', choices=PERIOD_CHOICES, default=1)
    price = models.DecimalField('Цена (руб)', max_digits=8, decimal_places=2)
    original_price = models.DecimalField('Исходная цена', max_digits=8, decimal_places=2, null=True, blank=True)
    description = models.TextField('Описание', blank=True)
    is_popular = models.BooleanField('Популярный', default=False)
    is_active = models.BooleanField('Активен', default=True)
    order = models.IntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Тарифный план'
        verbose_name_plural = 'Тарифные планы'
        ordering = ['order']

    def __str__(self):
        return f"{self.name} - {self.price}₽"

    def save(self, *args, **kwargs):
        # Автоматически рассчитываем скидку
        if not self.original_price:
            self.original_price = self.price * self.period
        super().save(*args, **kwargs)

    def discount_percent(self):
        """Процент скидки"""
        if self.original_price and self.original_price > self.price:
            discount = ((self.original_price - self.price) / self.original_price) * 100
            return int(discount)
        return 0


class UserSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    start_date = models.DateTimeField('Дата начала', auto_now_add=True)
    end_date = models.DateTimeField('Дата окончания')
    is_active = models.BooleanField('Активна', default=True)
    payment_id = models.CharField('ID платежа', max_length=100, blank=True)
    auto_renew = models.BooleanField('Автопродление', default=True)

    class Meta:
        verbose_name = 'Подписка пользователя'
        verbose_name_plural = 'Подписки пользователей'

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} до {self.end_date.date()}"

    def save(self, *args, **kwargs):
        # Автоматически устанавливаем дату окончания
        if not self.end_date:
            from datetime import datetime, timedelta
            self.end_date = datetime.now() + timedelta(days=self.plan.period * 30)
        super().save(*args, **kwargs)

    def days_remaining(self):
        """Дней до окончания подписки"""
        from datetime import datetime
        if self.end_date:
            remaining = (self.end_date - datetime.now()).days
            return max(0, remaining)
        return 0
