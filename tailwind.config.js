/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./spot/templates/**/*.html",
    "./spot/static/**/*.js",
    "./spot/services/**/*.py",
    "./spot/views*.py",
    "./spot/forms.py",
  ],
  theme: {
    extend: {
      colors: {
        'bf1-red': '#dc2626',
        'bf1-red-dark': '#b91c1c',
        'bf1-red-light': '#fee2e2',
        'bf1-gray': '#1f2937',
        'bf1-gray-dark': '#111827'
      },
    },
    fontFamily: {
      montserrat: ['Montserrat', 'sans-serif'],
      poppins: ['Poppins', 'sans-serif'],
    }
  },
  plugins: [],
}
