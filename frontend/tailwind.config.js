/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        studio: {
          cream: '#fff7f9',
          blush: '#ffe4ec',
          rose: '#fb7185',
          plum: '#831843',
          gold: '#f59e0b',
        },
      },
      boxShadow: {
        studio: '0 10px 40px -10px rgba(251, 113, 133, 0.35)',
      },
    },
  },
  plugins: [],
}

