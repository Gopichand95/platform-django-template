import { viteConfig } from "@workspace/eslint-config/vite"

export default [
  ...viteConfig,
  {
    ignores: ["dist/**", "src/services/**"],
  },
]
