/**
 * Telegram Mini App Visit Logger
 * Отслеживает открытия и закрытия Mini App
 */

(function() {
    'use strict';

    let sessionId = '';
    let isOpened = false;

    // Генерируем уникальный session_id
    function generateSessionId() {
        return 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    // Определяем платформу
    function getPlatform() {
        const tg = window.Telegram?.WebApp;
        if (!tg) return 'web';
        
        const platform = tg.platform || '';
        if (platform.toLowerCase().includes('android')) return 'android';
        if (platform.toLowerCase().includes('ios')) return 'ios';
        if (platform.toLowerCase().includes('web')) return 'web';
        if (platform.toLowerCase().includes('desktop')) return 'desktop';
        
        return 'unknown';
    }

    // Получаем start_param
    function getStartParam() {
        const tg = window.Telegram?.WebApp;
        if (!tg) return '';
        const initDataUnsafe = tg.initDataUnsafe || {};
        const startParam = initDataUnsafe.start_param || '';
        return startParam;
    }

    // Отправляем данные на сервер
    async function sendVisitData(action, data) {
        try {
            const response = await fetch('/telegram/visit/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                console.error('[VisitLog] Error:', response.status);
            }
            
            return await response.json();
        } catch (error) {
            console.error('[VisitLog] Network error:', error);
            return null;
        }
    }

    // Логируем открытие
    async function logOpen() {
        if (isOpened) return;
        
        sessionId = generateSessionId();
        isOpened = true;
        
        const tg = window.Telegram?.WebApp;
        const data = {
            user_id: tg?.initDataUnsafe?.user?.id,
            action: 'open',
            session_id: sessionId,
            platform: getPlatform(),
            start_param: getStartParam()
        };
        
        console.log('[VisitLog] Open:', data);
        await sendVisitData('open', data);
    }

    // Логируем закрытие
    async function logClose() {
        if (!isOpened) return;
        
        const tg = window.Telegram?.WebApp;
        const data = {
            user_id: tg?.initDataUnsafe?.user?.id,
            action: 'close',
            session_id: sessionId
        };
        
        console.log('[VisitLog] Close:', data);
        await sendVisitData('close', data);
        
        isOpened = false;
    }

    // Инициализация
    function init() {
        const tg = window.Telegram?.WebApp;
        
        if (!tg) {
            console.warn('[VisitLog] Telegram WebApp not found');
            return;
        }

        // Логируем открытие при инициализации
        logOpen();

        // Отслеживаем видимость страницы (когда пользователь сворачивает/разворачивает)
        document.addEventListener('visibilitychange', function() {
            if (document.visibilityState === 'hidden') {
                // Страница скрыта (пользователь переключился или закрыл)
                console.log('[VisitLog] Page hidden');
                logClose();
            } else {
                // Страница снова видима
                console.log('[VisitLog] Page visible');
                logOpen();
            }
        });

        // Закрытие перед уходом со страницы
        window.addEventListener('beforeunload', function() {
            // Отправляем синхронно (beacon API)
            const tg = window.Telegram?.WebApp;
            const data = {
                user_id: tg?.initDataUnsafe?.user?.id,
                action: 'close',
                session_id: sessionId
            };
            
            navigator.sendBeacon('/telegram/visit/', JSON.stringify(data));
            console.log('[VisitLog] Beforeunload:', data);
        });

        // Обработка кнопки "Назад" в Telegram
        if (tg.BackButton) {
            tg.BackButton.onClick(function() {
                logClose();
            });
        }

        // Слушаем событие закрытия от Telegram
        tg.onEvent('webAppClosed', function() {
            logClose();
        });
    }

    // Делаем функции доступными глобально
    window.initVisitLogger = init;
    window.VisitLogger = {
        logOpen: logOpen,
        logClose: logClose,
        getSessionId: function() { return sessionId; },
        isOpened: function() { return isOpened; }
    };

})();
