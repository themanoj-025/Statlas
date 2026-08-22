import nextPlugin from "@next/eslint-plugin-next";

export default [
  // Global ignores
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      "out/**",
      "public/**",
      "*.config.*",
      "playwright.config.*",
    ],
  },

  // Next.js core-web-vitals rules
  {
    name: "nextjs-core-web-vitals",
    plugins: {
      "@next/next": nextPlugin,
    },
    rules: {
      ...nextPlugin.configs["core-web-vitals"].rules,
    },
  },

  // Project-specific rules
  {
    name: "statlas-project",
    rules: {
      "@next/next/no-img-element": "warn",
      "no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "no-empty": ["error", { allowEmptyCatch: true }],
      "no-redeclare": "error",
    },
  },

  // Relax rules for test files
  {
    name: "test-overrides",
    files: ["**/*.test.ts", "**/*.test.tsx", "**/e2e/**"],
    rules: {
      "no-unused-vars": "off",
    },
  },
];
