import { defineConfig, globalIgnores } from "eslint/config";
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypeScript from "eslint-config-next/typescript";

export default defineConfig([
  ...nextCoreWebVitals,
  ...nextTypeScript,
  {
    files: ["components/**/*.{ts,tsx}", "features/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["@/lib/generated/**"],
              message: "Consume generated contracts through lib/api or lib/types, not UI code."
            }
          ]
        }
      ]
    }
  },
  ...["profile", "diary", "foods"].map((domain) => ({
    files: [`features/${domain}/**/*.{ts,tsx}`],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: [
                ...["profile", "diary", "foods"]
                  .filter((candidate) => candidate !== domain)
                  .map((candidate) => `@/features/${candidate}/**`)
              ],
              message: "Private feature modules must not import another feature's internals."
            },
            {
              group: ["@/lib/generated/**"],
              message: "Consume generated contracts through lib/api or lib/types, not feature code."
            }
          ]
        }
      ]
    }
  })),
  globalIgnores([
    ".next/**",
    "coverage/**",
    "node_modules/**",
    "out/**",
    "playwright-report/**",
    "public/sw.js",
    "test-results/**"
  ])
]);
