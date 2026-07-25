/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/templates/**/*.html', // Look for templates inside the app folder
    './app/static/**/*.js', // Look for JS files inside the app folder
  ],
  theme: {
    extend: {
      colors: {
        primary: 'rgb(12, 39, 136)',
        'primary-dark': 'rgb(8, 26, 91)',
        'primary-light': 'rgb(20, 60, 180)',
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Oxygen',
          'Ubuntu',
          'Cantarell',
          'sans-serif',
        ],
      },
    },
  },
  plugins: [],
};
