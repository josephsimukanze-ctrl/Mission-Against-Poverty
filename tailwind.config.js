/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./**/templates/**/*.html",
    "./**/*.py",
    "./static/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        mapnavy:   "#16253d",
        mapgreen:  "#1e9e5f",
        mapbg:     "#f8fafc",
        mapborder: "#e2e8f0",
      },
    },
  },
  plugins: [],
};
