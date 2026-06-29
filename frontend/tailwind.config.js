/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'wc-blue': '#1e40af',
        'wc-light-blue': '#3b82f6',
        'wc-gold': '#fbbf24',
        'wc-dark': '#0f172a',
      },
      fontFamily: {
        'sans': ['Montserrat', 'system-ui', 'sans-serif'],
        'display': ['"Bebas Neue"', 'Montserrat', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
