/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        trading: {
          dark: '#0B0E14',
          card: '#121824',
          border: '#1E293B',
          green: '#10B981',
          red: '#EF4444',
          accent: '#3B82F6',
          muted: '#64748B'
        }
      }
    },
  },
  plugins: [],
}
