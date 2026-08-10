import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: 'rgb(var(--bg) / <alpha-value>)',
        elev1: 'rgb(var(--bg-elev-1) / <alpha-value>)',
        elev2: 'rgb(var(--bg-elev-2) / <alpha-value>)',
        active: 'rgb(var(--bg-active) / <alpha-value>)',
        line: 'rgb(var(--border) / <alpha-value>)',
        'line-strong': 'rgb(var(--border-strong) / <alpha-value>)',
        'line-soft': 'rgb(var(--border-soft) / <alpha-value>)',
        ink: 'rgb(var(--ink) / <alpha-value>)',
        'ink-2': 'rgb(var(--ink-2) / <alpha-value>)',
        'ink-3': 'rgb(var(--ink-3) / <alpha-value>)',
        'ink-4': 'rgb(var(--ink-4) / <alpha-value>)',
        'ink-5': 'rgb(var(--ink-5) / <alpha-value>)',
        gold: 'rgb(var(--gold) / <alpha-value>)',
        'gold-primary': 'rgb(var(--gold-primary) / <alpha-value>)',
        'gold-deep': 'rgb(var(--gold-deep) / <alpha-value>)',
        'gold-tint': 'rgb(var(--gold-tint-bg) / <alpha-value>)',
        panel: 'rgb(var(--panel-bg) / <alpha-value>)',
        success: 'rgb(var(--success) / <alpha-value>)',
        warning: 'rgb(var(--warning) / <alpha-value>)',
        error: 'rgb(var(--error) / <alpha-value>)',
        info: 'rgb(var(--info) / <alpha-value>)',
      },
      fontFamily: {
        sans: [
          'Instrument Sans', '-apple-system', '"PingFang SC"', '"Hiragino Sans GB"',
          '"Microsoft YaHei"', '"Noto Sans SC"', 'sans-serif',
        ],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      boxShadow: {
        card: 'inset 0 1px 0 rgba(255,255,255,.04), 0 10px 30px -18px rgba(0,0,0,.8)',
        'inner-light': 'inset 0 1px 0 rgba(255,255,255,.05)',
        gold: '0 0 8px rgba(217,164,65,.45)',
        modal: '0 24px 64px -24px rgba(0,0,0,.9)',
      },
      borderRadius: {
        card: '10px',
      },
      keyframes: {
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseDot: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '.4' },
        },
      },
      animation: {
        fadeUp: 'fadeUp .3s cubic-bezier(.23,1,.32,1) both',
        pulseDot: 'pulseDot 1.4s ease-in-out infinite',
      },
    },
  },
  plugins: [],
} satisfies Config
