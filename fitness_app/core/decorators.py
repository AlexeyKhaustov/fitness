from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def full_access_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.session.get('restricted_access'):
            messages.error(request, 'Для выполнения этого действия необходимо принять обновлённые условия.')
            return redirect('accept_consent')
        return view_func(request, *args, **kwargs)
    return _wrapped_view