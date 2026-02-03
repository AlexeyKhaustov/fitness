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
    title = models.CharField('Название', max_length=100)
    file = models.FileField('Файл', upload_to='videos/%Y/%m/')
    description = models.TextField('Описание')
    is_free = models.BooleanField('Бесплатное', default=False)
    categories = models.ManyToManyField(
        Category,
        related_name='videos',
        blank=True,
        verbose_name='Категории'
    )
    duration = models.IntegerField('Длительность (секунды)', default=0)
    thumbnail = models.ImageField('Превью', upload_to='video_thumbs/%Y/%m/', blank=True, null=True)
    created_at = models.DateTimeField('Дата добавления', auto_now_add=True)
    views = models.IntegerField('Просмотры', default=0)

    # Новые поля для социальных функций (только для бесплатных видео)
    allow_comments = models.BooleanField('Разрешить комментарии', default=True)
    allow_sharing = models.BooleanField('Разрешить репост', default=True)
    allow_likes = models.BooleanField('Разрешить лайки', default=True)

    # Для премиум видео отключаем социальные функции
    def save(self, *args, **kwargs):
        if not self.is_free:
            self.allow_comments = False
            self.allow_sharing = False
            self.allow_likes = False
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Видео'
        verbose_name_plural = 'Видео'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('video_detail', args=[str(self.id)])

    def get_duration_display(self):
        minutes = self.duration // 60
        seconds = self.duration % 60
        return f"{minutes:02d}:{seconds:02d}"

    def increment_views(self):
        self.views += 1
        self.save(update_fields=['views'])

    def likes_count(self):
        return self.comments.filter(is_like=True).count()

    def comments_count(self):
        return self.comments.filter(is_like=False).count()


class VideoComment(models.Model):
    """Комментарии к видео (только для бесплатных видео)"""
    video = models.ForeignKey(
        Video,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Видео'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='video_comments',
        verbose_name='Пользователь'
    )
    text = models.TextField('Текст комментария', max_length=1000)
    is_like = models.BooleanField('Это лайк', default=False)

    # ПОЛЕ ДЛЯ ОТВЕТОВ
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Родительский комментарий'
    )

    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    # Модерация
    is_approved = models.BooleanField('Одобрен', default=True)
    is_edited = models.BooleanField('Редактировался', default=False)

    class Meta:
        verbose_name = 'Комментарий к видео'
        verbose_name_plural = 'Комментарии к видео'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['video', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        if self.is_like:
            return f"Лайк от {self.user.username} к видео {self.video.title}"
        return f"Комментарий от {self.user.username} к видео {self.video.title}"

    def save(self, *args, **kwargs):
        # Проверяем, что комментарии разрешены для этого видео
        if not self.video.allow_comments and not self.is_like:
            raise ValueError("Комментарии запрещены для этого видео")
        if not self.video.allow_likes and self.is_like:
            raise ValueError("Лайки запрещены для этого видео")

        # Отмечаем как отредактированный
        if self.pk:
            self.is_edited = True

        super().save(*args, **kwargs)

    # МЕТОД ДЛЯ ПОЛУЧЕНИЯ ОТВЕТОВ
    def get_replies(self):
        """Получить все ответы на комментарий"""
        return VideoComment.objects.filter(parent=self, is_approved=True)

    def replies_count(self):
        """Количество ответов на комментарий"""
        return VideoComment.objects.filter(parent=self, is_approved=True).count()


class Banner(models.Model):
    title = models.CharField('Заголовок', max_length=200)
    subtitle = models.TextField('Подзаголовок', max_length=500, blank=True)
    button_text = models.CharField('Текст кнопки', max_length=50, default='Смотреть')
    button_link = models.CharField('Ссылка кнопки', max_length=200, default='/')
    image = models.ImageField('Изображение', upload_to='banners/')
    image_mobile = models.ImageField('Изображение (мобильное)', upload_to='banners/mobile/', blank=True)

    # Управление отображением текста
    show_title = models.BooleanField('Показывать заголовок', default=True)
    show_subtitle = models.BooleanField('Показывать подзаголовок', default=True)

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


class Marathon(models.Model):
    """Марафон - только разовая покупка, НЕ по подписке"""
    title = models.CharField('Название марафона', max_length=200)
    slug = models.SlugField('URL', max_length=200, unique=True)

    # Описание для продающей страницы
    short_description = models.CharField('Краткое описание', max_length=300, blank=True)
    full_description = models.TextField('Полное описание', blank=True)

    # Визуал
    thumbnail = models.ImageField('Превью', upload_to='marathons/', blank=True)
    banner_color = models.CharField('Цвет баннера', max_length=7, default='#6366f1',
                                    help_text='HEX цвет (например: #6366f1 для фиолетового)')

    # Цена и доступ (ТОЛЬКО разовая покупка)
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2, default=0)

    # Связи
    teaser_videos = models.ManyToManyField(  # ← ИЗМЕНИЛИ НАЗВАНИЕ
        Video,
        related_name='marathon_teasers',
        blank=True,
        verbose_name='Тизерные видео',
        help_text='БЕСПЛАТНЫЕ видео для ознакомления с марафоном. Эти видео будут видны всем пользователям до покупки.'
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marathons',
        verbose_name='Связанная категория',
        help_text='Для навигации (необязательно)'
    )

    # Управление
    is_active = models.BooleanField('Активен', default=True)
    is_featured = models.BooleanField('Рекомендуемый', default=False)
    order = models.IntegerField('Порядок', default=0)

    # Статистика
    sales_count = models.IntegerField('Продано', default=0, editable=False)

    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Марафон'
        verbose_name_plural = 'Марафоны'
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('marathon_detail', args=[self.slug])

    def teaser_videos_count(self):
        """Количество бесплатных тизерных видео"""
        return self.teaser_videos.filter(is_free=True).count()

    def marathon_videos_count(self):
        """Количество эксклюзивных видео марафона"""
        return self.marathon_videos.count()

    def total_videos_count(self):
        """Общее количество видео (тизеры + эксклюзивные)"""
        return self.teaser_videos_count() + self.marathon_videos_count()

    def get_duration_minutes(self):
        """Общая длительность всех эксклюзивных видео в минутах"""
        total_seconds = self.marathon_videos.aggregate(total=models.Sum('duration'))['total'] or 0
        return total_seconds // 60

    def increment_sales(self):
        """Увеличить счетчик продаж"""
        self.sales_count += 1
        self.save(update_fields=['sales_count'])


class MarathonAccess(models.Model):
    """Доступ пользователя к марафону (покупка)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='marathon_accesses')
    marathon = models.ForeignKey(Marathon, on_delete=models.CASCADE, related_name='accesses')

    # Платежная информация
    purchased_at = models.DateTimeField('Дата покупки', auto_now_add=True)
    amount_paid = models.DecimalField('Сумма оплаты', max_digits=10, decimal_places=2)
    payment_id = models.CharField('ID платежа', max_length=100, blank=True)

    # Статус
    is_active = models.BooleanField('Активен', default=True)

    # Ограничение по времени (если нужно)
    valid_until = models.DateTimeField('Действует до', null=True, blank=True)

    class Meta:
        unique_together = ['user', 'marathon']
        verbose_name = 'Доступ к марафону'
        verbose_name_plural = 'Доступы к марафонам'
        ordering = ['-purchased_at']

    def __str__(self):
        return f"{self.user.username} → {self.marathon.title}"

    def is_valid(self):
        """Проверяет, действует ли доступ"""
        if not self.is_active:
            return False
        if self.valid_until and timezone.now() > self.valid_until:
            return False
        return True

    def days_remaining(self):
        """Осталось дней доступа"""
        if self.valid_until:
            remaining = (self.valid_until - timezone.now()).days
            return max(0, remaining)
        return None  # Бессрочный доступ


class MarathonVideo(models.Model):
    """Видео, доступное только через покупку марафона"""
    marathon = models.ForeignKey(
        Marathon,
        on_delete=models.CASCADE,
        related_name='marathon_videos',
        verbose_name='Марафон'
    )

    title = models.CharField('Название', max_length=200)
    file = models.FileField('Файл', upload_to='marathon_videos/%Y/%m/')
    description = models.TextField('Описание', blank=True)
    duration = models.IntegerField('Длительность (секунды)', default=0)
    thumbnail = models.ImageField('Превью', upload_to='marathon_thumbs/%Y/%m/', blank=True, null=True)
    order = models.IntegerField('Порядок', default=0)

    # Статистика
    views = models.IntegerField('Просмотры', default=0)

    # Для видео марафонов ВСЕГДА отключаем социальные функции
    allow_comments = models.BooleanField('Разрешить комментарии', default=False)
    allow_sharing = models.BooleanField('Разрешить репост', default=False)
    allow_likes = models.BooleanField('Разрешить лайки', default=False)

    created_at = models.DateTimeField('Дата добавления', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Видео марафона'
        verbose_name_plural = 'Видео марафонов'
        ordering = ['marathon', 'order', 'created_at']

    def __str__(self):
        return f"{self.marathon.title}: {self.title}"

    def get_absolute_url(self):
        return reverse('marathon_video_detail', kwargs={
            'marathon_slug': self.marathon.slug,
            'video_id': self.id
        })

    def get_duration_display(self):
        minutes = self.duration // 60
        seconds = self.duration % 60
        return f"{minutes:02d}:{seconds:02d}"

    def increment_views(self):
        self.views += 1
        self.save(update_fields=['views'])
