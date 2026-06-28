/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#f3f6fb',
        nav: '#162033',
        panel: '#ffffff',
        panel2: '#f7f9fc',
        edge: '#d8e0eb',
        ink: '#172033',
        dim: '#617089',
        neon: '#0f9f6e',
        cyan: '#1d73c9',
        magenta: '#7c3aed',
        amber: '#b7791f',
        danger: '#c2410c',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'Segoe UI', 'Arial', 'sans-serif'],
        mono: [
          'JetBrains Mono',
          'Fira Code',
          'SFMono-Regular',
          'Menlo',
          'Consolas',
          'monospace',
        ],
      },
      boxShadow: {
        glow: '0 1px 2px rgba(15,23,42,0.2), 0 0 0 1px rgba(16,185,129,0.18)',
        'glow-cyan': '0 1px 2px rgba(15,23,42,0.2), 0 0 0 1px rgba(56,189,248,0.18)',
      },
      keyframes: {
        pulseband: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.55' },
        },
        flashin: {
          '0%': { backgroundColor: 'rgba(16,185,129,0.18)' },
          '100%': { backgroundColor: 'transparent' },
        },
      },
      animation: {
        pulseband: 'pulseband 1.6s ease-in-out infinite',
        flashin: 'flashin 1.2s ease-out 1',
      },
    },
  },
  plugins: [],
};
