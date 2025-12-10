import type { PlopTypes } from '@turbo/gen';

export default function generator(plop: PlopTypes.NodePlopAPI): void {
  // Helper to convert to kebab-case
  plop.setHelper('kebabCase', (text: string) => {
    return text
      .replace(/([a-z])([A-Z])/g, '$1-$2')
      .replace(/[\s_]+/g, '-')
      .toLowerCase();
  });

  // Helper to convert to camelCase
  plop.setHelper('camelCase', (text: string) => {
    return text
      .replace(/[-_](.)/g, (_, c) => c.toUpperCase())
      .replace(/^(.)/, (c) => c.toLowerCase());
  });

  // Helper to convert to PascalCase
  plop.setHelper('pascalCase', (text: string) => {
    return text
      .replace(/[-_](.)/g, (_, c) => c.toUpperCase())
      .replace(/^(.)/, (c) => c.toUpperCase());
  });

  // Generator for creating a new Vite React-TS app
  plop.setGenerator('vite-app', {
    description: 'Create a new Vite + React + TypeScript app in apps/',
    prompts: [
      {
        type: 'input',
        name: 'name',
        message: 'What is the name of the new app? (kebab-case)',
        validate: (input: string) => {
          if (!input) {
            return 'App name is required';
          }
          if (input.includes(' ')) {
            return 'App name cannot include spaces (use kebab-case)';
          }
          if (!/^[a-z][a-z0-9-]*$/.test(input)) {
            return 'App name must be in kebab-case (lowercase letters, numbers, and hyphens only)';
          }
          return true;
        },
      },
      {
        type: 'input',
        name: 'description',
        message: 'Description of the app:',
        default: 'A new Vite React TypeScript app',
      },
      {
        type: 'confirm',
        name: 'includeTanstackQuery',
        message: 'Include TanStack Query?',
        default: true,
      },
      {
        type: 'confirm',
        name: 'includeReactRouter',
        message: 'Include React Router?',
        default: true,
      },
    ],
    actions: (data) => {
      const actions: PlopTypes.ActionType[] = [
        // Create package.json
        {
          type: 'add',
          path: '{{ turbo.paths.root }}/apps/{{ kebabCase name }}/package.json',
          templateFile: 'templates/vite-app/package.json.hbs',
        },
        // Create vite.config.ts
        {
          type: 'add',
          path: '{{ turbo.paths.root }}/apps/{{ kebabCase name }}/vite.config.ts',
          templateFile: 'templates/vite-app/vite.config.ts.hbs',
        },
        // Create tsconfig files
        {
          type: 'add',
          path: '{{ turbo.paths.root }}/apps/{{ kebabCase name }}/tsconfig.json',
          templateFile: 'templates/vite-app/tsconfig.json.hbs',
        },
        {
          type: 'add',
          path: '{{ turbo.paths.root }}/apps/{{ kebabCase name }}/tsconfig.app.json',
          templateFile: 'templates/vite-app/tsconfig.app.json.hbs',
        },
        {
          type: 'add',
          path: '{{ turbo.paths.root }}/apps/{{ kebabCase name }}/tsconfig.node.json',
          templateFile: 'templates/vite-app/tsconfig.node.json.hbs',
        },
        // Create eslint.config.js
        {
          type: 'add',
          path: '{{ turbo.paths.root }}/apps/{{ kebabCase name }}/eslint.config.js',
          templateFile: 'templates/vite-app/eslint.config.js.hbs',
        },
        // Create index.html
        {
          type: 'add',
          path: '{{ turbo.paths.root }}/apps/{{ kebabCase name }}/index.html',
          templateFile: 'templates/vite-app/index.html.hbs',
        },
        // Create src/main.tsx
        {
          type: 'add',
          path: '{{ turbo.paths.root }}/apps/{{ kebabCase name }}/src/main.tsx',
          templateFile: 'templates/vite-app/src/main.tsx.hbs',
        },
        // Create src/App.tsx
        {
          type: 'add',
          path: '{{ turbo.paths.root }}/apps/{{ kebabCase name }}/src/App.tsx',
          templateFile: 'templates/vite-app/src/App.tsx.hbs',
        },
        // Create src/index.css
        {
          type: 'add',
          path: '{{ turbo.paths.root }}/apps/{{ kebabCase name }}/src/index.css',
          templateFile: 'templates/vite-app/src/index.css.hbs',
        },
        // Create src/vite-env.d.ts
        {
          type: 'add',
          path: '{{ turbo.paths.root }}/apps/{{ kebabCase name }}/src/vite-env.d.ts',
          templateFile: 'templates/vite-app/src/vite-env.d.ts.hbs',
        },
        // Create components
        {
          type: 'add',
          path: '{{ turbo.paths.root }}/apps/{{ kebabCase name }}/src/components/error-boundary.tsx',
          templateFile: 'templates/vite-app/src/components/error-boundary.tsx.hbs',
        },
        {
          type: 'add',
          path: '{{ turbo.paths.root }}/apps/{{ kebabCase name }}/src/components/loading-spinner.tsx',
          templateFile: 'templates/vite-app/src/components/loading-spinner.tsx.hbs',
        },
        // Create features directory structure
        {
          type: 'add',
          path: '{{ turbo.paths.root }}/apps/{{ kebabCase name }}/src/features/.gitkeep',
          template: '',
        },
        // Create public directory
        {
          type: 'add',
          path: '{{ turbo.paths.root }}/apps/{{ kebabCase name }}/public/.gitkeep',
          template: '',
        },
        // Create README
        {
          type: 'add',
          path: '{{ turbo.paths.root }}/apps/{{ kebabCase name }}/README.md',
          templateFile: 'templates/vite-app/README.md.hbs',
        },
      ];

      // Add router.tsx if React Router is included
      if (data?.includeReactRouter) {
        actions.push({
          type: 'add',
          path: '{{ turbo.paths.root }}/apps/{{ kebabCase name }}/src/router.tsx',
          templateFile: 'templates/vite-app/src/router.tsx.hbs',
        });
      }

      return actions;
    },
  });

  // Generator for creating a new package
  plop.setGenerator('package', {
    description: 'Create a new package in packages/',
    prompts: [
      {
        type: 'input',
        name: 'name',
        message: 'What is the name of the package? (without @workspace/ prefix, kebab-case)',
        validate: (input: string) => {
          if (!input) {
            return 'Package name is required';
          }
          if (input.includes(' ')) {
            return 'Package name cannot include spaces (use kebab-case)';
          }
          if (!/^[a-z][a-z0-9-]*$/.test(input)) {
            return 'Package name must be in kebab-case (lowercase letters, numbers, and hyphens only)';
          }
          return true;
        },
      },
      {
        type: 'list',
        name: 'packageType',
        message: 'What type of package?',
        choices: [
          { name: 'React Component Library', value: 'react-library' },
          { name: 'TypeScript Utility Library', value: 'typescript-library' },
          { name: 'Configuration Package', value: 'config' },
        ],
      },
      {
        type: 'input',
        name: 'description',
        message: 'Description of the package:',
        default: 'A new workspace package',
      },
    ],
    actions: (data) => {
      const packageType = data?.packageType || 'typescript-library';
      const actions: PlopTypes.ActionType[] = [
        // Create package.json
        {
          type: 'add',
          path: '{{ turbo.paths.root }}/packages/{{ kebabCase name }}/package.json',
          templateFile: `templates/package/${packageType}/package.json.hbs`,
        },
        // Create tsconfig.json
        {
          type: 'add',
          path: '{{ turbo.paths.root }}/packages/{{ kebabCase name }}/tsconfig.json',
          templateFile: `templates/package/${packageType}/tsconfig.json.hbs`,
        },
        // Create README
        {
          type: 'add',
          path: '{{ turbo.paths.root }}/packages/{{ kebabCase name }}/README.md',
          templateFile: `templates/package/${packageType}/README.md.hbs`,
        },
      ];

      // Add type-specific files
      if (packageType === 'react-library') {
        actions.push(
          {
            type: 'add',
            path: '{{ turbo.paths.root }}/packages/{{ kebabCase name }}/src/index.ts',
            templateFile: 'templates/package/react-library/src/index.ts.hbs',
          },
          {
            type: 'add',
            path: '{{ turbo.paths.root }}/packages/{{ kebabCase name }}/src/components/.gitkeep',
            template: '',
          },
          {
            type: 'add',
            path: '{{ turbo.paths.root }}/packages/{{ kebabCase name }}/eslint.config.js',
            templateFile: 'templates/package/react-library/eslint.config.js.hbs',
          },
        );
      } else if (packageType === 'typescript-library') {
        actions.push({
          type: 'add',
          path: '{{ turbo.paths.root }}/packages/{{ kebabCase name }}/src/index.ts',
          templateFile: 'templates/package/typescript-library/src/index.ts.hbs',
        });
      } else if (packageType === 'config') {
        actions.push({
          type: 'add',
          path: '{{ turbo.paths.root }}/packages/{{ kebabCase name }}/index.js',
          templateFile: 'templates/package/config/index.js.hbs',
        });
      }

      return actions;
    },
  });
}
