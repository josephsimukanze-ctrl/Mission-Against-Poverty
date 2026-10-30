/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',

  content: [
    "./templates/**/*.html",
    "./**/templates/**/*.html",
    "./**/*.py",
    "./static/**/*.js",
  ],

  theme: {
    extend: {
      colors: {
        // Brand colours (light mode)
        mapnavy:   "#16253d",
        mapgreen:  "#1e9e5f",
        mapbg:     "#f8fafc",
        mapborder: "#e2e8f0",

        // Extra shades used across components
        "mapnavy-700":  "#0f1a2b",
        "mapnavy-900":  "#0a121f",
        "mapgreen-600": "#188a52",
        "mapgreen-50":  "#ecfdf5",
      },

      boxShadow: {
        "card-hover": "0 8px 24px -8px rgba(16, 24, 40, 0.12)",
      },
    },
  },

  plugins: [],
};