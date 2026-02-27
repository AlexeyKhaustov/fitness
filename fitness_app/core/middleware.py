from django.shortcuts import redirect
from .models import DocumentVersion, UserConsent

class ConsentMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Список путей, которые доступны без согласия
            exempt_paths = [
                '/accept-consent/',
                '/accounts/logout/',
                '/admin/',
                '/static/',
                '/media/',
            ]
            # Проверяем, начинается ли текущий путь с одного из exempt_paths
            if not any(request.path.startswith(path) for path in exempt_paths):
                if not self.has_valid_consents(request.user):
                    request.session['next_url'] = request.path
                    return redirect('accept_consent')
        return self.get_response(request)


    def has_valid_consents(self, user):
        active_versions = DocumentVersion.objects.filter(is_active=True).select_related('document')
        consented_version_ids = UserConsent.objects.filter(
            user=user,
            document_version__in=active_versions
        ).values_list('document_version_id', flat=True)
        return set(active_versions.values_list('id', flat=True)) == set(consented_version_ids)