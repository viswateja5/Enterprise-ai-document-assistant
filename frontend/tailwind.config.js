/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        chatgpt: {
          sidebar: '#171717',
          main: '#212121',
          input: '#2f2f2f',
          userbubble: '#2f2f2f',
          botbubble: '#212121'
        }
      }
    },
  },
  plugins: [],
}
