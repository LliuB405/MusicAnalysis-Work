/**
 * Theme Manager — light / dark / system
 * ============================================================
 * 用法：
 *   ThemeManager.set('dark')            // 强制暗色
 *   ThemeManager.set('light')           // 强制亮色
 *   ThemeManager.set('system')          // 跟随系统
 *   ThemeManager.get()                  // 'dark' | 'light'
 *   ThemeManager.toggle()               // 在 dark/light 间切换
 *   ThemeManager.onChange(cb)           // 订阅主题变化
 *
 * 主题设置保存在 localStorage['_pulse_theme']
 * 实际应用通过给 <html> 标签加 data-theme="dark|light" 实现。
 * CSS 使用 [data-theme="dark"] / [data-theme="light"] 选择器覆盖变量。
 */
(function () {
    'use strict';
    const STORAGE_KEY = '_pulse_theme';
    const VALID_MODES = ['light', 'dark', 'system'];

    function getMode() {
        try {
            const v = localStorage.getItem(STORAGE_KEY);
            if (VALID_MODES.includes(v)) return v;
        } catch (e) {}
        return 'dark'; // 默认暗色
    }

    function getEffectiveTheme(mode) {
        if (mode === 'system') {
            return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
        }
        return mode;
    }

    let _mode = getMode();
    const _listeners = new Set();

    function applyTheme() {
        const eff = getEffectiveTheme(_mode);
        document.documentElement.setAttribute('data-theme', eff);
        // meta theme-color
        const meta = document.querySelector('meta[name="theme-color"]');
        if (meta) meta.setAttribute('content', eff === 'light' ? '#f4f5f7' : '#06070a');
        _listeners.forEach(cb => { try { cb(eff, _mode); } catch (e) {} });
    }

    // 监听系统主题变化
    window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', () => {
        if (_mode === 'system') applyTheme();
    });

    // 跨标签页同步
    window.addEventListener('storage', (e) => {
        if (e.key === STORAGE_KEY) {
            _mode = getMode();
            applyTheme();
        }
    });

    window.ThemeManager = {
        get() { return getEffectiveTheme(_mode); },
        getMode() { return _mode; },
        set(mode) {
            if (!VALID_MODES.includes(mode)) return;
            _mode = mode;
            try { localStorage.setItem(STORAGE_KEY, mode); } catch (e) {}
            applyTheme();
        },
        toggle() {
            const eff = getEffectiveTheme(_mode);
            this.set(eff === 'dark' ? 'light' : 'dark');
        },
        onChange(cb) { _listeners.add(cb); return () => _listeners.delete(cb); },
        // 渲染一个主题切换按钮到指定容器
        renderButton(container) {
            if (!container) return;
            container.innerHTML = `
                <button class="theme-toggle" id="_tm_btn" title="切换主题">
                    <span class="tm-icon" data-icon="auto">🌗</span>
                    <span class="tm-label"></span>
                </button>
            `;
            const btn = container.querySelector('#_tm_btn');
            const icon = container.querySelector('.tm-icon');
            const label = container.querySelector('.tm-label');

            const update = () => {
                const icons = { light: '☀️', dark: '🌙', system: '🌗' };
                const labels = { light: '亮色', dark: '暗色', system: '系统' };
                icon.textContent = icons[_mode] || '🌗';
                if (label) label.textContent = labels[_mode] || '';
            };
            update();

            btn.addEventListener('click', () => {
                const seq = ['dark', 'light', 'system'];
                const next = seq[(seq.indexOf(_mode) + 1) % seq.length];
                this.set(next);
                update();
            });
            this.onChange(update);
        }
    };

    // 启动时应用一次
    applyTheme();
})();
