document.addEventListener('DOMContentLoaded', function() {
    // Функция для определения мобильного устройства
    function isMobileDevice() {
        return window.innerWidth < 640 || ('ontouchstart' in window);
    }

    // Функция для адаптации под мобильные
    function adjustForMobile() {
        const isMobile = isMobileDevice();
        const cards = document.querySelectorAll('.category-card');

        cards.forEach(card => {
            if (isMobile) {
                // На мобильных: убираем hover-эффекты, добавляем touch-эффекты
                card.addEventListener('touchstart', function(e) {
                    this.style.backgroundColor = 'rgba(139, 92, 246, 0.1)';
                }, { passive: true });

                card.addEventListener('touchend', function(e) {
                    this.style.backgroundColor = '';
                }, { passive: true });

                card.addEventListener('touchcancel', function(e) {
                    this.style.backgroundColor = '';
                }, { passive: true });
            }
        });
    }

    // Функция для проверки количества категорий
    function checkCategoryCount() {
        const grid = document.querySelector('.categories-grid');
        const cards = document.querySelectorAll('.category-card');

        if (grid && cards.length === 1) {
            grid.style.justifyContent = 'center';
        }
    }

    // Вызываем при загрузке
    adjustForMobile();
    checkCategoryCount();

    // Вызываем при изменении размера окна (с debounce)
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            adjustForMobile();
            checkCategoryCount();
        }, 250);
    });

    // Для iOS добавляем обработку :active состояний
    document.addEventListener('touchstart', function() {}, { passive: true });
});