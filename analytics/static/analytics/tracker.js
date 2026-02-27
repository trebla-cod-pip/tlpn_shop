/**
 * Analytics Tracker для Django E-commerce
 * Собирает события: page_view, scroll, clicks, cart, checkout, web_vitals
 * 
 * Подключение в base.html:
 * <script src="{% static 'analytics/tracker.js' %}" defer></script>
 */

(function(window, document) {
    'use strict';

    // Конфигурация
    const CONFIG = {
        endpoint: window.ANALYTICS_ENDPOINT || '/analytics/track/',
        sessionTimeout: 30 * 60 * 1000, // 30 минут
        batchEvents: true,              // Отправлять события пачками
        batchSize: 10,                  // Размер пачки
        batchDelay: 5000,               // Задержка отправки (мс)
        sampleRate: 1.0,                // 100% трафика
        debug: false,                   // Режим отладки
    };

    // Состояние
    let state = {
        sessionId: null,
        userId: null,
        events: [],
        scrollDepth: 0,
        scrollThresholds: [25, 50, 75, 100],
        scrollTracked: {},
        startTime: Date.now(),
        pageViewId: generateId(),
    };
    let batchTimer = null;

    // Логгер
    const log = (...args) => {
        if (CONFIG.debug) console.log('[Analytics]', ...args);
    };

    // Генерация ID
    function generateId() {
        return 'sess_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    }

    // Проверка opt-out
    function isOptOut() {
        return document.cookie.includes('analytics_optout=1');
    }

    // Инициализация
    function init() {
        if (isOptOut()) {
            log('Opt-out detected, skipping initialization');
            return;
        }

        if (batchTimer) {
            clearInterval(batchTimer);
            batchTimer = null;
        }
        if (CONFIG.batchEvents) {
            batchTimer = setInterval(() => {
                flushEvents();
            }, CONFIG.batchDelay);
        }

        // Получаем session ID
        state.sessionId = getSessionId();
        
        // Отправляем page view
        trackPageView();

        // Настраиваем трекеры
        setupScrollTracking();
        setupClickTracking();
        setupWebVitalsTracking();
        setupVisibilityTracking();
        setupBeforeUnload();

        log('Initialized with session:', state.sessionId);
    }

    // Получение/создание session ID
    function getSessionId() {
        let sessionId = sessionStorage.getItem('analytics_session_id');
        
        if (!sessionId) {
            sessionId = generateId();
            sessionStorage.setItem('analytics_session_id', sessionId);
        }
        
        return sessionId;
    }

    // Отправка события
    function trackEvent(eventType, eventName, data = {}) {
        if (isOptOut()) return;

        const event = {
            session_id: state.sessionId,
            event_type: eventType,
            event_name: eventName,
            url: window.location.href,
            page_title: document.title,
            meta: {
                ...data,
                viewport: `${window.innerWidth}x${window.innerHeight}`,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            },
            timestamp: new Date().toISOString(),
        };

        state.events.push(event);
        log('Event tracked:', eventType, eventName);

        // Отправляем если набралась пачка
        if (CONFIG.batchEvents && state.events.length >= CONFIG.batchSize) {
            flushEvents();
        } else if (!CONFIG.batchEvents) {
            flushEvents();
        }
    }

    // Отправка пачки событий
    function flushEvents() {
        if (state.events.length === 0) return;

        const eventsToSend = [...state.events];
        state.events = [];

        // Используем sendBeacon для надёжной отправки
        const payload = JSON.stringify({ events: eventsToSend });
        
        if (navigator.sendBeacon) {
            const beaconBody = new Blob([payload], { type: 'application/json' });
            navigator.sendBeacon(CONFIG.endpoint, beaconBody);
        } else {
            // Fallback для старых браузеров
            fetch(CONFIG.endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: payload,
                keepalive: true,
            }).catch(err => log('Send error:', err));
        }

        log('Flushed', eventsToSend.length, 'events');
    }

    // ========================================================================
    // Page View
    // ========================================================================
    function trackPageView() {
        trackEvent('page_view', 'page_view', {
            path: window.location.pathname,
            search: window.location.search,
            hash: window.location.hash,
            referrer: document.referrer,
        });
    }

    // ========================================================================
    // Scroll Depth Tracking
    // ========================================================================
    function setupScrollTracking() {
        let ticking = false;

        window.addEventListener('scroll', () => {
            if (!ticking) {
                window.requestAnimationFrame(() => {
                    const scrollPercent = calculateScrollDepth();
                    trackScrollDepth(scrollPercent);
                    ticking = false;
                });
                ticking = true;
            }
        }, { passive: true });
    }

    function calculateScrollDepth() {
        const scrollTop = window.scrollY || window.pageYOffset;
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;
        return docHeight > 0 ? Math.round((scrollTop / docHeight) * 100) : 0;
    }

    function trackScrollDepth(depth) {
        state.scrollThresholds.forEach(threshold => {
            if (depth >= threshold && !state.scrollTracked[threshold]) {
                state.scrollTracked[threshold] = true;
                trackEvent('scroll_depth', `scroll_${threshold}%`, {
                    depth: threshold,
                    time_on_page: Math.round((Date.now() - state.startTime) / 1000),
                });
            }
        });
    }

    // ========================================================================
    // Click Tracking
    // ========================================================================
    function setupClickTracking() {
        document.addEventListener('click', (e) => {
            const target = e.target.closest('a, button, [data-track-click]');
            if (!target) return;

            // Трекаем только важные клики
            const selector = getSelector(target);
            const isTracked = (
                target.hasAttribute('data-track-click') ||
                selector.includes('.add-to-cart') ||
                selector.includes('.checkout') ||
                selector.includes('.buy') ||
                target.tagName === 'A' && target.href && !target.href.startsWith('#')
            );

            if (isTracked) {
                trackEvent('click', 'element_click', {
                    element: target.tagName.toLowerCase(),
                    selector: selector,
                    text: target.innerText?.slice(0, 100) || target.getAttribute('aria-label') || '',
                    href: target.href || null,
                    target: target.target || null,
                });
            }
        }, { passive: true });
    }

    function getSelector(el) {
        const parts = [];
        while (el && el.nodeType === Node.ELEMENT_NODE) {
            let selector = el.nodeName.toLowerCase();
            if (el.id) {
                selector += `#${el.id}`;
                parts.unshift(selector);
                break;
            } else if (el.className) {
                selector += '.' + el.className.split(' ').filter(Boolean).join('.');
            }
            parts.unshift(selector);
            el = el.parentElement;
        }
        return parts.join(' > ');
    }

    // ========================================================================
    // Cart & Checkout Events (автоматическое определение)
    // ========================================================================
    function trackAddToCart(productId, productName, price, quantity = 1) {
        trackEvent('add_to_cart', 'add_to_cart', {
            product_id: productId,
            product_name: productName,
            price: price,
            quantity: quantity,
        });
    }

    function trackRemoveFromCart(productId) {
        trackEvent('remove_from_cart', 'remove_from_cart', {
            product_id: productId,
        });
    }

    function trackCheckoutStart(cartValue, itemCount) {
        trackEvent('checkout_start', 'checkout_start', {
            cart_value: cartValue,
            item_count: itemCount,
        });
    }

    function trackCheckoutStep(step, data = {}) {
        trackEvent('checkout_step', `checkout_${step}`, {
            step: step,
            ...data,
        });
    }

    function trackPurchase(orderId, revenue, items, tax = 0, shipping = 0) {
        trackEvent('purchase', 'purchase', {
            order_id: orderId,
            revenue: revenue,
            tax: tax,
            shipping: shipping,
            items: items, // [{product_id, name, price, quantity}]
        });
    }

    // ========================================================================
    // Web Vitals Tracking
    // ========================================================================
    function setupWebVitalsTracking() {
        // Используем Web Vitals library (подключить отдельно)
        // https://github.com/GoogleChrome/web-vitals
        
        if (typeof webVitals !== 'undefined') {
            // LCP - Largest Contentful Paint
            webVitals.onLCP((metric) => {
                trackEvent('web_vital', 'LCP', {
                    value: metric.value,
                    rating: metric.rating,
                    delta: metric.delta,
                });
            });

            // FID - First Input Delay (устарел, заменён на INP)
            webVitals.onFID?.((metric) => {
                trackEvent('web_vital', 'FID', {
                    value: metric.value,
                    rating: metric.rating,
                });
            });

            // INP - Interaction to Next Paint
            webVitals.onINP?.((metric) => {
                trackEvent('web_vital', 'INP', {
                    value: metric.value,
                    rating: metric.rating,
                });
            });

            // CLS - Cumulative Layout Shift
            webVitals.onCLS((metric) => {
                trackEvent('web_vital', 'CLS', {
                    value: metric.value,
                    rating: metric.rating,
                });
            });

            // TTFB - Time to First Byte
            webVitals.onTTFB?.((metric) => {
                trackEvent('web_vital', 'TTFB', {
                    value: metric.value,
                    rating: metric.rating,
                });
            });
        } else {
            // Fallback - базовое измерение
            trackBasicWebVitals();
        }
    }

    function trackBasicWebVitals() {
        // LCP approximation
        if (PerformanceObserver) {
            try {
                const lcpObserver = new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    const lastEntry = entries[entries.length - 1];
                    trackEvent('web_vital', 'LCP', {
                        value: lastEntry.startTime,
                        rating: lastEntry.startTime < 2500 ? 'good' : lastEntry.startTime < 4000 ? 'needs-improvement' : 'poor',
                    });
                });
                lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
            } catch (e) {
                log('LCP observer error:', e);
            }
        }
    }

    // ========================================================================
    // Visibility & Before Unload
    // ========================================================================
    function setupVisibilityTracking() {
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'hidden') {
                // Пользователь ушёл со страницы
                trackEvent('custom', 'page_hidden', {
                    time_on_page: Math.round((Date.now() - state.startTime) / 1000),
                });
                flushEvents();
            } else {
                // Пользователь вернулся
                state.startTime = Date.now();
                state.pageViewId = generateId();
            }
        });
    }

    function setupBeforeUnload() {
        window.addEventListener('beforeunload', () => {
            flushEvents();
        });
    }

    // ========================================================================
    // Public API
    // ========================================================================
    window.AnalyticsTracker = {
        track: trackEvent,
        trackPageView,
        trackAddToCart,
        trackRemoveFromCart,
        trackCheckoutStart,
        trackCheckoutStep,
        trackPurchase,
        flush: flushEvents,
        optOut: () => {
            document.cookie = 'analytics_optout=1; path=/; max-age=31536000';
            state.events = [];
            if (batchTimer) {
                clearInterval(batchTimer);
                batchTimer = null;
            }
        },
        optIn: () => {
            document.cookie = 'analytics_optout=0; path=/; max-age=-1';
            init();
        },
        setUserId: (userId) => {
            state.userId = userId;
        },
        getConfig: () => ({ ...CONFIG }),
        setConfig: (newConfig) => {
            Object.assign(CONFIG, newConfig);
            if (batchTimer) {
                clearInterval(batchTimer);
                batchTimer = null;
            }
            if (CONFIG.batchEvents) {
                batchTimer = setInterval(() => {
                    flushEvents();
                }, CONFIG.batchDelay);
            }
        },
    };

    // Авто-инициализация после загрузки DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})(window, document);
