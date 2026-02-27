from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.contrib.admin.views.decorators import staff_member_required
from fitness_app.core import admin_views

urlpatterns = [
    # Админские экшены для документов
    path('admin/create-document-version/<int:doc_id>/',
         staff_member_required(admin_views.create_document_version),
         name='create_document_version'),
    path('admin/set-active-version/<int:version_id>/',
         staff_member_required(admin_views.set_active_version),
         name='set_active_version'),

    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('fitness_app.core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)