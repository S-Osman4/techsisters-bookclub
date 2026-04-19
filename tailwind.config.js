// tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: ["./app/templates/**/*.html", "./app/static/src/ts/**/*.ts"],
  theme: {
    extend: {
      colors: {
        dark: {
          bg: "#1A1A2E",
          surface: "#22223A",
          elevated: "#2C2C48",
          input: "#353558",
          border: "#3C3C60",
        },
        primary: {
          DEFAULT: "#FF6B6B",
          dark: "#E85555",
          light: "#FF8E8E",
        },
        secondary: {
          DEFAULT: "#4ECDC4",
          dark: "#3AB8AF",
          light: "#6ED9D3",
        },
        accent: {
          DEFAULT: "#FFE66D",
          dark: "#FFD93D",
        },
      },
      fontFamily: {
        heading: ['"Playfair Display"', "serif"],
        body: ["Poppins", "sans-serif"],
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.5rem",
      },
      boxShadow: {
        card: "0 4px 20px -4px rgba(0,0,0,0.08)",
        "card-hover": "0 20px 40px -8px rgba(255,107,107,0.2)",
      },
      backgroundImage: {
        "gradient-primary": "linear-gradient(135deg, #FF6B6B 0%, #FF8E8E 100%)",
        "gradient-secondary":
          "linear-gradient(135deg, #4ECDC4 0%, #6ED9D3 100%)",
        "gradient-hero":
          "linear-gradient(135deg, #FF6B6B 0%, #FF8E8E 40%, #4ECDC4 100%)",
      },
    },
  },
  plugins: [require("@tailwindcss/forms"), require("@tailwindcss/line-clamp")],
};
