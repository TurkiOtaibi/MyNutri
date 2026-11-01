import { registerHooks } from "node:module";
import { minimatch } from "minimatch";

// These plugins still call require("minimatch") as a function. Expose the
// patched implementation with that signature when ESLint loads their rules.
export { minimatch as "module.exports" };

const legacyPlugin = /\/node_modules\/eslint-plugin-(?:import|jsx-a11y|react)\//;
registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier === "minimatch" && legacyPlugin.test(context.parentURL ?? "")) {
      return { url: import.meta.url, shortCircuit: true };
    }
    return nextResolve(specifier, context);
  },
});
