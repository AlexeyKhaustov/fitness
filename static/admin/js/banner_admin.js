// Скрипт для админки баннеров

document.addEventListener('DOMContentLoaded', function() {
    // Автоматическое обновление типа баннера при изменении настроек
    const updateBannerType = function() {
        const isClickable = document.getElementById('id_is_clickable');
        const showButton = document.getElementById('id_show_button');
        const buttonOnHover = document.getElementById('id_button_on_hover');

        if (!isClickable || !showButton) return;

        const typeInfo = document.querySelector('.display-type-info');
        if (!typeInfo) return;

        let typeText = '';
        let typeIcon = '';

        if (!isClickable.checked && !showButton.checked) {
            typeText = '📷 Статичный баннер';
            typeIcon = '📷';
        } else if (isClickable.checked && !showButton.checked) {
            typeText = '🔗 Весь баннер кликабелен';
            typeIcon = '🔗';
        } else if (isClickable.checked && showButton.checked && !buttonOnHover.checked) {
            typeText = '🔼 Кнопка всегда видна';
            typeIcon = '🔼';
        } else if (isClickable.checked && showButton.checked && buttonOnHover.checked) {
            typeText = '✨ Кнопка при наведении';
            typeIcon = '✨';
        }

        // Обновляем текст
        const typeElement = typeInfo.querySelector('strong');
        if (typeElement) {
            typeElement.innerHTML = `📋 Текущий тип баннера: <span style="color: #059669;">${typeText}</span>`;
        }
    };

    // Вешаем обработчики на чекбоксы
    document.getElementById('id_is_clickable')?.addEventListener('change', updateBannerType);
    document.getElementById('id_show_button')?.addEventListener('change', updateBannerType);
    document.getElementById('id_button_on_hover')?.addEventListener('change', updateBannerType);

    // Инициализация при загрузке
    updateBannerType();

    // Подсказка для приоритета
    const priorityField = document.querySelector('.field-priority input');
    if (priorityField) {
        priorityField.addEventListener('input', function(e) {
            const value = parseInt(e.target.value) || 0;
            const hint = document.getElementById('priority-hint');

            if (!hint) {
                const newHint = document.createElement('div');
                newHint.id = 'priority-hint';
                newHint.style.cssText = 'margin-top: 5px; font-size: 13px; color: #6b7280;';
                priorityField.parentNode.appendChild(newHint);
            }

            const hintElement = document.getElementById('priority-hint');
            if (value >= 10) {
                hintElement.innerHTML = '⭐ Высокий приоритет - будет показан первым';
                hintElement.style.color = '#f59e0b';
            } else if (value >= 5) {
                hintElement.innerHTML = '✅ Средний приоритет';
                hintElement.style.color = '#10b981';
            } else {
                hintElement.innerHTML = '📋 Низкий приоритет';
                hintElement.style.color = '#6b7280';
            }
        });

        // Триггерим событие для показа начальной подсказки
        priorityField.dispatchEvent(new Event('input'));
    }

    // Подсказка для цвета текста
    const textColorField = document.querySelector('.field-text_color input');
    if (textColorField) {
        textColorField.addEventListener('input', function(e) {
            const color = e.target.value;
            const preview = document.getElementById('text-color-preview');

            if (!preview) {
                const newPreview = document.createElement('div');
                newPreview.id = 'text-color-preview';
                newPreview.style.cssText = 'margin-top: 5px; padding: 8px; border-radius: 4px; font-size: 13px; display: flex; align-items: center; gap: 8px;';
                textColorField.parentNode.appendChild(newPreview);
            }

            const previewElement = document.getElementById('text-color-preview');
            if (color) {
                previewElement.innerHTML = `
                    <span>Пример текста</span>
                    <span style="background: ${color}; color: white; padding: 2px 8px; border-radius: 3px;">${color}</span>
                `;
                previewElement.style.background = '#f3f4f6';
            }
        });

        if (textColorField.value) {
            textColorField.dispatchEvent(new Event('input'));
        }
    }
});