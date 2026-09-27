/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bgDark: '#0f0f1b',
        bgPanel: '#1a1a2e',
        bgHeader: '#161625',
        borderDark: '#2a2a40',
        textPri: '#e4e4ef',
        textSec: '#8f8fb3',
        accent: '#6366f1',
      }
    },
  },
  plugins: [],
}