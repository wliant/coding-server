import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import { TaskTable } from "../../src/components/tasks/TaskTable";
import type { TaskResponse } from "../../src/client/types.gen";

const mockTasks: TaskResponse[] = [
  {
    id: "task-1",
    project: { id: "proj-1", name: "Project Alpha", source_type: "new" },
    dev_agent_type: "spec_driven_development",
    test_agent_type: "generic_testing",
    requirements: "Build a REST API",
    status: "pending",
    created_at: "2026-03-01T10:00:00Z",
    updated_at: "2026-03-01T10:00:00Z",
    error_message: null,
  },
  {
    id: "task-2",
    project: { id: "proj-2", name: "Project Beta", source_type: "existing" },
    dev_agent_type: "spec_driven_development",
    test_agent_type: "generic_testing",
    requirements: "Add authentication",
    status: "aborted",
    created_at: "2026-03-01T09:00:00Z",
    updated_at: "2026-03-01T09:30:00Z",
    error_message: null,
  },
  {
    id: "task-3",
    project: { id: "proj-3", name: null, source_type: "new" },
    dev_agent_type: "spec_driven_development",
    test_agent_type: "generic_testing",
    requirements: "Setup CI/CD pipeline",
    status: "completed",
    created_at: "2026-03-01T08:00:00Z",
    updated_at: "2026-03-01T11:00:00Z",
    error_message: null,
  },
];

describe("TaskTable", () => {
  it("renders column headers", () => {
    render(<TaskTable tasks={mockTasks} />);

    expect(screen.getByText(/project/i)).toBeInTheDocument();
    expect(screen.getByText(/dev agent/i)).toBeInTheDocument();
    expect(screen.getByText(/test agent/i)).toBeInTheDocument();
    expect(screen.getByText(/status/i)).toBeInTheDocument();
    expect(screen.getByText(/submitted/i)).toBeInTheDocument();
  });

  it("renders all provided tasks as rows", () => {
    render(<TaskTable tasks={mockTasks} />);

    expect(screen.getByText("Build a REST API")).toBeInTheDocument();
    expect(screen.getByText("Add authentication")).toBeInTheDocument();
    expect(screen.getByText("Setup CI/CD pipeline")).toBeInTheDocument();
  });

  it("shows empty state message when tasks list is empty", () => {
    render(<TaskTable tasks={[]} />);

    expect(screen.getByText(/no tasks/i)).toBeInTheDocument();
  });

  it("filters rows by requirements text when search is used", () => {
    render(<TaskTable tasks={mockTasks} />);

    const searchInput = screen.getByPlaceholderText(/search/i);
    fireEvent.change(searchInput, { target: { value: "REST API" } });

    expect(screen.getByText("Build a REST API")).toBeInTheDocument();
    expect(screen.queryByText("Add authentication")).not.toBeInTheDocument();
    expect(screen.queryByText("Setup CI/CD pipeline")).not.toBeInTheDocument();
  });

  it("filters rows by project name when search is used", () => {
    render(<TaskTable tasks={mockTasks} />);

    const searchInput = screen.getByPlaceholderText(/search/i);
    fireEvent.change(searchInput, { target: { value: "Beta" } });

    expect(screen.getByText("Add authentication")).toBeInTheDocument();
    expect(screen.queryByText("Build a REST API")).not.toBeInTheDocument();
  });

  it("shows empty state when search matches nothing", () => {
    render(<TaskTable tasks={mockTasks} />);

    const searchInput = screen.getByPlaceholderText(/search/i);
    fireEvent.change(searchInput, { target: { value: "xyznonexistent" } });

    expect(screen.getByText(/no tasks match/i)).toBeInTheDocument();
  });

  it("shows abort button for pending tasks", () => {
    render(<TaskTable tasks={mockTasks} />);

    const abortButtons = screen.getAllByRole("button", { name: /abort/i });
    expect(abortButtons.length).toBeGreaterThan(0);
  });

  it("shows edit button for aborted tasks", () => {
    render(<TaskTable tasks={mockTasks} />);

    const editLinks = screen.getAllByRole("link", { name: /edit/i });
    expect(editLinks.length).toBeGreaterThan(0);
  });
});
