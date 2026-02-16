document.addEventListener('DOMContentLoaded', function() {
    // Добавляем предпросмотр цвета для HEX полей
    const colorFields = document.querySelectorAll('input[type="text"][id*="color"]');

    colorFields.forEach(function(field) {
        // Создаем контейнер для предпросмотра
        const preview = document.createElement('span');
        preview.className = 'color-preview';
        preview.style.backgroundColor = field.value || '#ffffff';

        // Вставляем после поля
        field.parentNode.insertBefore(preview, field.nextSibling);

        // Обновляем предпросмотр при изменении
        field.addEventListener('input', function() {
            preview.style.backgroundColor = field.value || '#ffffff';
        });

        // Добавляем пипетку для выбора цвета
        const pickerBtn = document.createElement('button');
        pickerBtn.type = 'button';
        pickerBtn.textContent = '🎨';
        pickerBtn.title = 'Выбрать цвет';
        pickerBtn.style.marginLeft = '5px';
        pickerBtn.style.padding = '2px 6px';
        pickerBtn.style.border = '1px solid #ccc';
        pickerBtn.style.borderRadius = '3px';
        pickerBtn.style.background = '#f8f9fa';
        pickerBtn.style.cursor = 'pointer';

        pickerBtn.addEventListener('click', function() {
            // Используем нативный input color
            const colorInput = document.createElement('input');
            colorInput.type = 'color';
            colorInput.value = field.value.replace('#', '') ? '#' + field.value.replace('#', '') : '#ffffff';

            colorInput.addEventListener('input', function(e) {
                field.value = e.target.value;
                preview.style.backgroundColor = e.target.value;
                field.dispatchEvent(new Event('input', { bubbles: true }));
            });

            colorInput.click();
        });

        field.parentNode.insertBefore(pickerBtn, preview.nextSibling);
    });
});