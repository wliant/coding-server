import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import { TaskForm } from "../../src/components/tasks/TaskForm";
import type { ProjectSummary } from "../../src/client/types.gen";

const mockProjects: ProjectSummary[] = [
  { id: "project-1", name: "Project Alpha", source_type: "new" },
  { id: "project-2", name: "Project Beta", source_type: "existing" },
];

describe("TaskForm", () => {
  it("renders project select, dev agent select, test agent select, and requirements textarea", () => {
    const onSubmit = jest.fn();
    render(<TaskForm projects={mockProjects} onSubmit={onSubmit} />);

    expect(screen.getByRole("combobox", { name: /project/i })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /dev agent/i })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /test agent/i })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /requirements/i })).toBeInTheDocument();
  });

  it("submit button is disabled when requirements is empty", () => {
    const onSubmit = jest.fn();
    render(<TaskForm projects={mockProjects} onSubmit={onSubmit} />);

    const submitButton = screen.getByRole("button", { name: /submit/i });
    expect(submitButton).toBeDisabled();
  });

  it("submit button is disabled when no project selected", () => {
    const onSubmit = jest.fn();
    render(<TaskForm projects={mockProjects} onSubmit={onSubmit} />);

    const requirementsInput = screen.getByRole("textbox", { name: /requirements/i });
    fireEvent.change(requirementsInput, { target: { value: "Build something" } });

    const submitButton = screen.getByRole("button", { name: /submit/i });
    expect(submitButton).toBeDisabled();
  });

  it("submit button is disabled when isSubmitting is true", () => {
    const onSubmit = jest.fn();
    render(
      <TaskForm
        projects={mockProjects}
        onSubmit={onSubmit}
        isSubmitting={true}
        initialValues={{
          project_type: "new",
          dev_agent_type: "spec_driven_development",
          test_agent_type: "generic_testing",
          requirements: "Some requirement",
        }}
      />
    );

    const submitButton = screen.getByRole("button", { name: /submit/i });
    expect(submitButton).toBeDisabled();
  });

  it("calls onSubmit with correct values when form is valid and submitted", async () => {
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    render(
      <TaskForm
        projects={mockProjects}
        onSubmit={onSubmit}
        initialValues={{
          project_type: "new",
          dev_agent_type: "spec_driven_development",
          test_agent_type: "generic_testing",
          requirements: "",
        }}
      />
    );

    const requirementsInput = screen.getByRole("textbox", { name: /requirements/i });
    await userEvent.type(requirementsInput, "Build a REST API");

    const submitButton = screen.getByRole("button", { name: /submit/i });
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          requirements: "Build a REST API",
          dev_agent_type: "spec_driven_development",
          test_agent_type: "generic_testing",
        })
      );
    });
  });
});
