import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        accent: {
          DEFAULT: "#ea580c", // Warm subtle orange
          hover: "#c2410c",
          light: "#ffedd5",
          muted: "rgba(234, 88, 12, 0.12)",
        },
      },
    },
  },
  plugins: [],
};
export default config;
