from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Document, DocumentVersion

def create_document_version(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id)
    current = doc.current_version

    # Вычисляем следующий номер версии
    last_version = DocumentVersion.objects.filter(document=doc).order_by('-version_number').first()
    new_version_number = (last_version.version_number + 1) if last_version else 1

    new_version = DocumentVersion.objects.create(
        document=doc,
        version_number=new_version_number,   # обязательно передаём номер
        text=current.text if current else '',
        is_active=False
    )
    messages.success(request,
                     f'Создана новая версия документа {doc.get_type_display()} №{new_version.version_number}. Отредактируйте текст и активируйте её.')
    return redirect('admin:core_documentversion_change', new_version.id)

def set_active_version(request, version_id):
    version = get_object_or_404(DocumentVersion, id=version_id)
    doc = version.document
    # Деактивируем все остальные версии этого документа
    DocumentVersion.objects.filter(document=doc, is_active=True).update(is_active=False)
    version.is_active = True
    version.save()
    doc.current_version = version
    doc.save()
    messages.success(request,
                     f'Версия {version.version_number} документа {doc.get_type_display()} теперь активна.')
    return redirect('admin:core_documentversion_changelist')