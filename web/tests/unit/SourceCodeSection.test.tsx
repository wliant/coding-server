import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { SourceCodeSection } from "../../src/components/tasks/SourceCodeSection";

// Mock next-themes
jest.mock("next-themes", () => ({
  useTheme: () => ({ resolvedTheme: "light" }),
}));

// Mock react-syntax-highlighter
jest.mock("react-syntax-highlighter", () => {
  return {
    __esModule: true,
    default: ({ children }: { children: string }) => <pre>{children}</pre>,
  };
});
jest.mock("react-syntax-highlighter/dist/esm/styles/hljs", () => ({
  githubGist: {},
  atomOneDark: {},
}));

// Mock workerClient
jest.mock("../../src/lib/workerClient", () => ({
  getWorkerBaseUrl: (url: string | null | undefined) => url ?? "http://localhost:8001",
  fetchFileTree: jest.fn().mockResolvedValue({
    root: "/workspace",
    entries: [
      { name: "README.md", path: "README.md", type: "file", size: 100 },
    ],
  }),
  fetchFileContent: jest.fn().mockResolvedValue({
    path: "README.md",
    content: "# Hello",
    size: 7,
    is_binary: false,
  }),
  fetchDiffList: jest.fn().mockResolvedValue({
    changed_files: [],
    total_additions: 0,
    total_deletions: 0,
  }),
  fetchFileDiff: jest.fn().mockResolvedValue({
    path: "",
    diff: "",
    is_new_file: false,
  }),
}));

describe("SourceCodeSection", () => {
  it("shows both Source and Diff tabs by default", () => {
    render(
      <SourceCodeSection taskId="task-1" workerUrl="http://localhost:8001" />
    );

    expect(screen.getByText("Source")).toBeInTheDocument();
    expect(screen.getByText("Diff")).toBeInTheDocument();
  });

  it("hides Diff tab when isNewProject is true", () => {
    render(
      <SourceCodeSection
        taskId="task-1"
        workerUrl="http://localhost:8001"
        isNewProject={true}
      />
    );

    expect(screen.getByText("Source Code")).toBeInTheDocument();
    expect(screen.queryByText("Diff")).not.toBeInTheDocument();
  });

  it("shows Diff tab when isNewProject is false", () => {
    render(
      <SourceCodeSection
        taskId="task-1"
        workerUrl="http://localhost:8001"
        isNewProject={false}
      />
    );

    expect(screen.getByText("Source")).toBeInTheDocument();
    expect(screen.getByText("Diff")).toBeInTheDocument();
  });
});
