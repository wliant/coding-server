import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import { FileTree } from "../../src/components/tasks/FileTree";
import type { FileEntry } from "../../src/lib/fileProxyClient";

const mockEntries: FileEntry[] = [
  { name: "src", path: "src", type: "directory" },
  { name: "main.py", path: "src/main.py", type: "file", size: 200 },
  { name: "utils.py", path: "src/utils.py", type: "file", size: 150 },
  { name: "tests", path: "tests", type: "directory" },
  { name: "test_main.py", path: "tests/test_main.py", type: "file", size: 100 },
  { name: "README.md", path: "README.md", type: "file", size: 50 },
];

describe("FileTree", () => {
  it("renders all files and directories", () => {
    render(
      <FileTree entries={mockEntries} selectedPath={null} onSelect={jest.fn()} />
    );

    expect(screen.getByText("src")).toBeInTheDocument();
    expect(screen.getByText("tests")).toBeInTheDocument();
    expect(screen.getByText("README.md")).toBeInTheDocument();
  });

  it("expands top-level directories by default", () => {
    render(
      <FileTree entries={mockEntries} selectedPath={null} onSelect={jest.fn()} />
    );

    // Files inside top-level dirs should be visible
    expect(screen.getByText("main.py")).toBeInTheDocument();
    expect(screen.getByText("test_main.py")).toBeInTheDocument();
  });

  it("highlights selected file", () => {
    render(
      <FileTree
        entries={mockEntries}
        selectedPath="src/main.py"
        onSelect={jest.fn()}
      />
    );

    const selectedButton = screen.getByText("main.py");
    expect(selectedButton.closest("button")).toHaveClass("bg-muted");
  });

  it("calls onSelect when a file is clicked", () => {
    const onSelect = jest.fn();
    render(
      <FileTree entries={mockEntries} selectedPath={null} onSelect={onSelect} />
    );

    fireEvent.click(screen.getByText("README.md"));
    expect(onSelect).toHaveBeenCalledWith("README.md");
  });

  it("shows empty state when no entries", () => {
    render(
      <FileTree entries={[]} selectedPath={null} onSelect={jest.fn()} />
    );

    expect(screen.getByText(/no files/i)).toBeInTheDocument();
  });

  // Filter tests
  it("filters files by name (case-insensitive)", () => {
    render(
      <FileTree
        entries={mockEntries}
        selectedPath={null}
        onSelect={jest.fn()}
        filter="main"
      />
    );

    expect(screen.getByText("main.py")).toBeInTheDocument();
    expect(screen.getByText("test_main.py")).toBeInTheDocument();
    expect(screen.queryByText("README.md")).not.toBeInTheDocument();
    expect(screen.queryByText("utils.py")).not.toBeInTheDocument();
  });

  it("shows parent directories for filtered files", () => {
    render(
      <FileTree
        entries={mockEntries}
        selectedPath={null}
        onSelect={jest.fn()}
        filter="utils"
      />
    );

    expect(screen.getByText("src")).toBeInTheDocument();
    expect(screen.getByText("utils.py")).toBeInTheDocument();
    expect(screen.queryByText("tests")).not.toBeInTheDocument();
  });

  it("shows 'no files match' when filter matches nothing", () => {
    render(
      <FileTree
        entries={mockEntries}
        selectedPath={null}
        onSelect={jest.fn()}
        filter="nonexistent"
      />
    );

    expect(screen.getByText(/no files match/i)).toBeInTheDocument();
  });

  it("shows all files when filter is empty string", () => {
    render(
      <FileTree
        entries={mockEntries}
        selectedPath={null}
        onSelect={jest.fn()}
        filter=""
      />
    );

    expect(screen.getByText("README.md")).toBeInTheDocument();
    expect(screen.getByText("main.py")).toBeInTheDocument();
  });
});
