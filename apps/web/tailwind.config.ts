import type { Config } from "tailwindcss"

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        positive: "#10b981",
        negative: "#ef4444",
        warning:  "#f59e0b",
        btc:      "#f97316",
        accent:   "#6366f1",
      },
      backgroundColor: {
        base:     "var(--bg-base)",
        surface:  "var(--bg-surface)",
        elevated: "var(--bg-elevated)",
        hover:    "var(--bg-hover)",
      },
      borderColor: {
        DEFAULT: "var(--border)",
        subtle:  "var(--border-subtle)",
      },
      textColor: {
        primary:   "var(--text-primary)",
        secondary: "var(--text-secondary)",
        tertiary:  "var(--text-tertiary)",
      },
      keyframes: {
        shimmer: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0"  },
        },
      },
      animation: {
        shimmer: "shimmer 1.5s infinite linear",
      },
    },
  },
  plugins: [],
}

export default config
