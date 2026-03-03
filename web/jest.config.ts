import type { Config } from "jest";
import nextJest from "next/jest.js";

const createJestConfig = nextJest({
  dir: "./",
});

const config: Config = {
  coverageProvider: "v8",
  testEnvironment: "jsdom",
  testMatch: ["**/tests/unit/**/*.test.ts", "**/tests/unit/**/*.test.tsx"],
  setupFiles: ["<rootDir>/jest.setup.ts"],
};

export default createJestConfig(config);
