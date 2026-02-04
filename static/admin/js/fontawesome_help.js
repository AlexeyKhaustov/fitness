// fontawesome_help.js - упрощенная рабочая версия
document.addEventListener('DOMContentLoaded', function() {
    console.log('FontAwesome Helper loaded');

    // Часть 1: Помощник для выбора иконок (оставляем как было)
    const iconField = document.querySelector('#id_icon');
    if (iconField) {
        console.log('Setting up icon selector...');

        const iconCategories = {
            'Фитнес и спорт': ['dumbbell', 'running', 'heart-pulse', 'fire', 'weight-hanging'],
            'Здоровье и питание': ['apple-whole', 'utensils', 'carrot', 'fish', 'leaf'],
            'Другие': ['bolt', 'star', 'trophy', 'users', 'mountain']
        };

        const helpContainer = document.createElement('div');
        helpContainer.className = 'icon-helper';
        helpContainer.innerHTML = `
            <h4>Выберите иконку:</h4>
            <div class="icon-grid-container">
                ${Object.entries(iconCategories).map(([cat, icons]) => `
                    <div style="margin-bottom: 15px;">
                        <div style="font-weight: 600; color: #4b5563; margin-bottom: 8px; font-size: 13px;">${cat}</div>
                        <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                            ${icons.map(iconName => `
                                <div class="icon-item" data-icon="${iconName}"
                                     style="width: 45px; height: 45px; display: flex; flex-direction: column;
                                            align-items: center; justify-content: center;
                                            background: #f3f4f6; border-radius: 6px; cursor: pointer;
                                            transition: all 0.2s; border: 1px solid #e5e7eb;">
                                    <i class="fa-solid fa-${iconName}" style="font-size: 16px; color: #4f46e5;"></i>
                                    <div style="font-size: 9px; margin-top: 2px; color: #6b7280;">${iconName}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        iconField.parentNode.insertBefore(helpContainer, iconField.nextSibling);

        document.querySelectorAll('.icon-item').forEach(item => {
            item.addEventListener('click', function() {
                const iconName = this.dataset.icon;
                iconField.value = iconName;

                // Подсветка
                document.querySelectorAll('.icon-item').forEach(i => {
                    i.style.background = '#f3f4f6';
                    i.style.borderColor = '#e5e7eb';
                });

                this.style.background = '#4f46e5';
                this.querySelector('i').style.color = 'white';
                this.style.borderColor = '#4f46e5';
            });
        });
    }

    // Часть 2: Превью картинки (оставляем как было)
    const imageField = document.querySelector('#id_image');
    if (imageField) {
        const imagePreview = document.createElement('div');
        imagePreview.className = 'image-preview-container';
        imagePreview.innerHTML = `<div id="current-image-preview"></div>`;

        imageField.parentNode.insertBefore(imagePreview, imageField.nextSibling);

        function updateImagePreview() {
            const preview = document.getElementById('current-image-preview');
            if (imageField.files && imageField.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    preview.innerHTML = `
                        <img src="${e.target.result}" style="max-width: 200px; max-height: 200px; border-radius: 8px;" />
                        <div style="color: #059669; margin-top: 8px; font-size: 13px;">
                            ✅ Загружено новое изображение
                        </div>
                    `;
                };
                reader.readAsDataURL(imageField.files[0]);
            } else if (imageField.dataset.imageUrl) {
                preview.innerHTML = `
                    <img src="${imageField.dataset.imageUrl}" style="max-width: 200px; max-height: 200px; border-radius: 8px;" />
                    <div style="color: #4f46e5; margin-top: 8px; font-size: 13px;">
                        📁 Текущее изображение
                    </div>
                `;
            }
        }

        imageField.addEventListener('change', updateImagePreview);
        updateImagePreview();
    }

    // Часть 3: КЛИКАБЕЛЬНЫЕ ЦВЕТОВЫЕ БЛОКИ - ОСНОВНАЯ ЧАСТЬ
    console.log('Setting up color blocks...');

    // Глобальная функция для копирования градиента
    window.copyGradientToField = function(gradient) {
        const colorField = document.getElementById('id_color');
        if (colorField) {
            colorField.value = gradient;

            // Фокус и выделение
            colorField.focus();
            colorField.select();

            // Показываем уведомление
            showNotification(`✓ Градиент скопирован!`);

            console.log('Gradient copied:', gradient);
        } else {
            console.error('Color field not found!');
        }
    };

    // Альтернативный способ: обработчики событий
    function setupColorBlocks() {
        const colorBlocks = document.querySelectorAll('.color-example');
        console.log(`Found ${colorBlocks.length} color blocks`);

        colorBlocks.forEach(block => {
            // Убираем inline onclick если есть
            block.removeAttribute('onclick');

            // Добавляем обработчик клика
            block.addEventListener('click', function() {
                const gradient = this.dataset.gradient;
                console.log('Block clicked, gradient:', gradient);

                if (gradient) {
                    window.copyGradientToField(gradient);

                    // Анимация
                    this.style.animation = 'pulse 0.6s';
                    setTimeout(() => {
                        this.style.animation = '';
                    }, 600);
                }
            });

            // Улучшаем внешний вид
            block.style.cursor = 'pointer';
            block.style.transition = 'all 0.3s';

            block.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-3px)';
                this.style.boxShadow = '0 8px 20px rgba(0,0,0,0.2)';
            });

            block.addEventListener('mouseleave', function() {
                this.style.transform = '';
                this.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
            });
        });
    }

    // Функция уведомления
    function showNotification(message) {
        // Удаляем старое
        const old = document.querySelector('.gradient-notification');
        if (old) old.remove();

        // Создаем новое
        const notification = document.createElement('div');
        notification.className = 'gradient-notification';
        notification.innerHTML = `
            <div style="
                position: fixed;
                top: 20px;
                right: 20px;
                background: linear-gradient(135deg, #10b981, #059669);
                color: white;
                padding: 12px 20px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
                display: flex;
                align-items: center;
                gap: 10px;
                z-index: 10000;
                animation: slideIn 0.3s ease-out;
            ">
                <i class="fa-solid fa-check-circle"></i>
                <span>${message}</span>
            </div>
        `;

        document.body.appendChild(notification);

        // Удаляем через 3 секунды
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    // Добавляем стили для анимаций
    const styles = document.createElement('style');
    styles.textContent = `
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(0.95); }
            100% { transform: scale(1); }
        }

        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }

        /* Стили для ночного режима */
        body.dark .color-example {
            border-color: rgba(255, 255, 255, 0.2) !important;
        }

        body.dark .color-example:hover {
            border-color: rgba(255, 255, 255, 0.4) !important;
        }
    `;
    document.head.appendChild(styles);

    // Запускаем настройку после загрузки
    setTimeout(setupColorBlocks, 100);

    console.log('FontAwesome Helper setup complete');
});