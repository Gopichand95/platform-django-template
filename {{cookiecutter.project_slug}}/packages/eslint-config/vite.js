import pluginReact from "eslint-plugin-react"
import pluginReactHooks from "eslint-plugin-react-hooks"
import pluginReactRefresh from "eslint-plugin-react-refresh"
import globals from "globals"

import { config as baseConfig } from "./base.js"

/**
 * A custom ESLint configuration for Vite React applications.
 *
 * @type {import("eslint").Linter.Config}
 */
export const viteConfig = [
  ...baseConfig,
  pluginReact.configs.flat.recommended,
  pluginReactRefresh.configs.vite,
  {
    languageOptions: {
      ...pluginReact.configs.flat.recommended.languageOptions,
      globals: {
        ...globals.browser,
      },
    },
  },
  {
    plugins: {
      "react-hooks": pluginReactHooks,
    },
    settings: { react: { version: "detect" } },
    rules: {
      ...pluginReactHooks.configs.recommended.rules,
      "react/react-in-jsx-scope": "off",
      "react/prop-types": "off",
    },
  },
]
