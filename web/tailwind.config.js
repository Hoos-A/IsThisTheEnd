/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        teal: {
          500: "#0ea5a4"
        }
      },
      boxShadow: {
        soft: "0 10px 40px rgba(14, 165, 164, 0.15)"
      }
    }
  },
  plugins: []
};
