/** @typedef  {import("prettier").Config} PrettierConfig */

/** @type { PrettierConfig } */
const config = {
  tabWidth: 2,
  useTabs: false,
  semi: true,
  printWidth: 100,
  singleQuote: true,
  arrowParens: 'always',
  endOfLine: 'lf',
  bracketSpacing: true,
  bracketSameLine: false,
  importOrder: [
    '^react$',
    '<THIRD_PARTY_MODULES>',
    '^@workspace/(.*)$', // package imports
    '^@/(.*)$', // app-specific imports
    '^[./]', // relative imports
  ],
  tailwindFunctions: ['tw', 'clsx', 'cn', 'cva'],
  tailwindStylesheet: './packages/ui/src/styles/globals.css',
  importOrderSeparation: true,
  importOrderSortSpecifiers: true,
  plugins: [
    '@trivago/prettier-plugin-sort-imports',
    'prettier-plugin-tailwindcss',
  ],
};

export default config;
