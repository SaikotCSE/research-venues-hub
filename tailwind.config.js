/** Tailwind build for VenuePulse. Rebuild with `npm run build:css` after changing templates. */
const colors = require("tailwindcss/colors");

module.exports = {
  darkMode: "class",
  // Classes built dynamically in templates (e.g. the milestone stepper's column count).
  safelist: ["sm:grid-cols-2", "sm:grid-cols-3", "sm:grid-cols-4", "sm:grid-cols-5", "sm:grid-cols-6"],
  content: [
    "./{venues,accounts,tracker,community,config}/**/*.html",
    "./{venues,accounts,tracker,community,config}/**/*.py",
    "./venues/static/venues/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: { brand: colors.indigo },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "Helvetica Neue", "Arial", "Noto Sans", "sans-serif", "Apple Color Emoji", "Segoe UI Emoji"],
      },
      keyframes: {
        "fade-in": { from: { opacity: "0", transform: "translateY(4px)" }, to: { opacity: "1", transform: "none" } },
        shimmer: { "100%": { transform: "translateX(100%)" } },
      },
      animation: { "fade-in": "fade-in .2s ease-out", shimmer: "shimmer 1.4s infinite" },
    },
  },
  plugins: [],
};
