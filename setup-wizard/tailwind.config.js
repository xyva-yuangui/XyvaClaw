/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f7ff',
          100: '#e0efff',
          200: '#b9dfff',
          300: '#7cc4ff',
          400: '#36a5ff',
          500: '#0c86f0',
          600: '#0068cd',
          700: '#0053a6',
          800: '#054789',
          900: '#0a3c71',
          950: '#07264b',
        },
      },
    },
  },
  plugins: [],
};
