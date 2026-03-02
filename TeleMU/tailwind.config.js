/** @type {import('tailwindcss').Config} */
export default {
	content: ["./src/mainview/**/*.{html,js,ts,jsx,tsx}"],
	theme: {
		extend: {
			colors: {
				telemu: {
					bg: "#1a1a1a",
					"bg-light": "#242424",
					"bg-lighter": "#2e2e2e",
					"bg-input": "#1e1e1e",
					border: "#3a3a3a",
					"border-light": "#4a4a4a",
					text: "#d4d4d4",
					"text-dim": "#888888",
					"text-bright": "#f0f0f0",
					accent: "#e8751a",
					"accent-hover": "#f08c3a",
					"accent-pressed": "#c85f10",
					amber: "#f5a623",
					red: "#d63031",
					green: "#27ae60",
					selection: "#3a3020",
				},
			},
		},
	},
	plugins: [],
};
