/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        mbi: {
          navy:  '#1a3a5c',
          orange:'#e87722',
          light: '#f0f4f8',
          steel: '#4a6278',
        },
      },
    },
  },
  plugins: [],
}
