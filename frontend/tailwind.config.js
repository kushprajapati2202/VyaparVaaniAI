/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#080C14',
        surface: '#0E1422',
        card: '#121B2E',
        'card-hover': '#18243E',
        border: 'rgba(255, 255, 255, 0.08)',
        'border-strong': 'rgba(255, 255, 255, 0.15)',
        saffron: {
          50: '#FFF7ED',
          100: '#FFEDD5',
          400: '#FB923C',
          500: '#F97316',
          600: '#EA580C',
          glow: 'rgba(249, 115, 22, 0.25)',
        },
        primary: {
          DEFAULT: '#0EA5E9',
          hover: '#0284C7',
          glow: '#38BDF8',
          soft: 'rgba(14, 165, 233, 0.15)',
        },
        success: {
          DEFAULT: '#10B981',
          bg: 'rgba(16, 185, 129, 0.12)',
          border: 'rgba(16, 185, 129, 0.3)',
        },
        warning: {
          DEFAULT: '#F59E0B',
          bg: 'rgba(245, 158, 11, 0.12)',
          border: 'rgba(245, 158, 11, 0.3)',
        },
        danger: {
          DEFAULT: '#F43F5E',
          bg: 'rgba(244, 63, 94, 0.12)',
          border: 'rgba(244, 63, 94, 0.3)',
        }
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Outfit', 'sans-serif'],
      },
      boxShadow: {
        'glow-saffron': '0 0 30px -5px rgba(249, 115, 22, 0.35)',
        'glow-teal': '0 0 30px -5px rgba(14, 165, 233, 0.35)',
        'glow-emerald': '0 0 30px -5px rgba(16, 185, 129, 0.35)',
        'card': '0 10px 30px -10px rgba(0, 0, 0, 0.5)',
      }
    },
  },
  plugins: [],
}
