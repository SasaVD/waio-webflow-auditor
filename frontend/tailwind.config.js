/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#2820FF",
        "primary-hover": "#1E18CC",
        "bg-light": "#FFFFFF",
        "bg-dark": "#000000",
        "bg-card": "#E3E8EF",
        "text-primary": "#000000",
        "text-body": "#333333",
        "text-muted": "#6B7280",
        "text-on-dark": "#FFFFFF",
        score: {
          excellent: "#22C55E",
          good: "#84CC16",
          "needs-improvement": "#EAB308",
          poor: "#F97316",
          critical: "#EF4444"
        }
      },
      fontFamily: {
        sans: ['Inter', 'Arial', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
