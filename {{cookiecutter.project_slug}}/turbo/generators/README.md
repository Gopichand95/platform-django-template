# Turborepo Generators

This directory contains Turborepo generators for creating new apps and packages in the monorepo.

## Available Generators

### 1. `vite-app` - Create a Vite React TypeScript App

Creates a new Vite + React + TypeScript application in the `apps/` directory.

**Usage:**

```bash
pnpm turbo gen vite-app
```

**Features:**

- **Vite 7** with React 19 and TypeScript
- **Tailwind CSS v4** with `@workspace/ui` integration
- **Optional TanStack Query** for data fetching
- **Optional React Router v7** for routing
- **Shared tooling configs** (TypeScript, ESLint, Prettier)
- **Django-compatible build output** (manifest.json, static paths)
- **Error Boundary** and Loading Spinner components
- **Feature-based folder structure** (`src/features/`)
- **Path aliases** (`@/` for src directory)

**Generated Structure:**

```
apps/your-app/
├── src/
│   ├── components/
│   │   ├── error-boundary.tsx
│   │   └── loading-spinner.tsx
│   ├── features/
│   ├── App.tsx
│   ├── main.tsx
│   ├── router.tsx (if React Router enabled)
│   ├── index.css
│   └── vite-env.d.ts
├── public/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.node.json
├── eslint.config.js
├── package.json
└── README.md
```

**Post-Generation Steps:**

1. Run `pnpm install` to install dependencies
2. Run `pnpm dev` to start the development server
3. Start building your app in `src/`

---

### 2. `package` - Create a New Package

Creates a new package in the `packages/` directory with three options:

#### React Component Library

Shared React components that can be used across apps.

**Usage:**

```bash
pnpm turbo gen package
# Select "React Component Library"
```

**Features:**

- TypeScript setup with `@workspace/typescript-config/react-library.json`
- ESLint config for React internal libraries
- Package exports for components, hooks, and lib
- React 19 as dependency

**Generated Structure:**

```
packages/your-package/
├── src/
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   └── index.ts
├── package.json
├── tsconfig.json
├── eslint.config.js
└── README.md
```

#### TypeScript Utility Library

Shared TypeScript utilities and functions.

**Usage:**

```bash
pnpm turbo gen package
# Select "TypeScript Utility Library"
```

**Features:**

- TypeScript setup with `@workspace/typescript-config/base.json`
- No React dependencies
- Simple exports configuration

**Generated Structure:**

```
packages/your-package/
├── src/
│   └── index.ts
├── package.json
├── tsconfig.json
└── README.md
```

#### Configuration Package

Shared configuration files (ESLint, TypeScript, Prettier, etc.).

**Usage:**

```bash
pnpm turbo gen package
# Select "Configuration Package"
```

**Features:**

- Minimal package.json
- Basic TypeScript config
- Configured for public publishing

**Generated Structure:**

```
packages/your-package/
├── index.js
├── package.json
├── tsconfig.json
└── README.md
```

---

## Generator Prompts

### Vite App Prompts

1. **App name** (kebab-case, required)
   - Must be lowercase with hyphens
   - Example: `my-new-app`

2. **Description** (optional)
   - Default: "A new Vite React TypeScript app"

3. **Include TanStack Query?** (default: yes)
   - Adds `@tanstack/react-query` for data fetching

4. **Include React Router?** (default: yes)
   - Adds `react-router` v7 and creates `router.tsx`

### Package Prompts

1. **Package name** (kebab-case, required, without `@workspace/` prefix)
   - Must be lowercase with hyphens
   - Example: `my-utils`
   - Will become `@workspace/my-utils`

2. **Package type** (required)
   - React Component Library
   - TypeScript Utility Library
   - Configuration Package

3. **Description** (optional)
   - Default: "A new workspace package"

---

## Template Variables

The generators use Handlebars templates with the following variables:

- `{{ name }}` - Original input name
- `{{ kebabCase name }}` - Kebab-case version (e.g., `my-app`)
- `{{ camelCase name }}` - Camel-case version (e.g., `myApp`)
- `{{ pascalCase name }}` - Pascal-case version (e.g., `MyApp`)
- `{{ description }}` - User-provided description
- `{{ includeTanstackQuery }}` - Boolean for TanStack Query (vite-app only)
- `{{ includeReactRouter }}` - Boolean for React Router (vite-app only)

---

## Extending Generators

### Adding a New Generator

1. Edit `turbo/generators/config.ts`
2. Add a new generator using `plop.setGenerator()`
3. Create templates in `turbo/generators/templates/your-generator/`
4. Use `.hbs` extension for Handlebars templates

### Adding Templates

Templates use Handlebars syntax:

```handlebars
{
  "name": "{{ kebabCase name }}",
  "version": "0.0.0"
}
```

Conditionals:

```handlebars
{{#if includeFeature}}
  // This will only appear if includeFeature is true
{{/if}}
```

---

## Best Practices

1. **Naming Convention**: Always use kebab-case for app and package names
2. **Workspace Protocol**: Use `workspace:*` for internal dependencies
3. **Shared Configs**: Leverage `@workspace/typescript-config`, `@workspace/eslint-config`, and `@workspace/prettier-config`
4. **Feature-Based Structure**: Organize apps by features in `src/features/`
5. **Path Aliases**: Use `@/` for app imports and `@workspace/package-name/*` for package imports

---

## Troubleshooting

### Generator Not Showing Up

- Ensure `config.ts` has the correct `plop.setGenerator()` call
- Check that template files exist in the correct directory
- Restart your terminal and try again

### Template Syntax Errors

- Verify Handlebars syntax is correct
- Check that variable names match those defined in prompts
- Ensure conditionals have matching opening and closing tags

### Missing Dependencies

- Run `pnpm install` in the root directory
- Check that `@turbo/gen` is installed in `package.json`

---

## Examples

### Create a New Dashboard App

```bash
pnpm turbo gen vite-app
# Name: dashboard
# Description: Admin dashboard application
# TanStack Query: Yes
# React Router: Yes
```

### Create a Shared Utilities Package

```bash
pnpm turbo gen package
# Name: utils
# Type: TypeScript Utility Library
# Description: Shared utility functions
```

### Create a Component Library

```bash
pnpm turbo gen package
# Name: design-system
# Type: React Component Library
# Description: Design system components
```

---

## Resources

- [Turborepo Generators Documentation](https://turbo.build/repo/docs/core-concepts/monorepos/code-generation)
- [Plop.js Documentation](https://plopjs.com/)
- [Handlebars Documentation](https://handlebarsjs.com/)
