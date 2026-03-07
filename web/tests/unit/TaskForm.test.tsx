import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import { TaskForm } from "../../src/components/tasks/TaskForm";
import type { AgentResponse } from "../../src/client/types.gen";

const mockAgents: AgentResponse[] = [
  { id: "agent-1", identifier: "spec_driven_development", display_name: "Spec-Driven Development", is_active: true },
  { id: "agent-2", identifier: "generic_testing", display_name: "Generic Testing", is_active: true },
];

describe("TaskForm", () => {
  it("renders project type select, agent select, and requirements textarea", () => {
    const onSubmit = jest.fn();
    render(<TaskForm agents={mockAgents} onSubmit={onSubmit} />);

    expect(screen.getByLabelText(/project type/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^agent$/i)).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /requirements/i })).toBeInTheDocument();
  });

  it("submit button is disabled when requirements is empty", () => {
    const onSubmit = jest.fn();
    render(<TaskForm agents={mockAgents} onSubmit={onSubmit} />);

    const submitButton = screen.getByRole("button", { name: /submit/i });
    expect(submitButton).toBeDisabled();
  });

  it("submit button is disabled when no agent selected", () => {
    const onSubmit = jest.fn();
    render(<TaskForm agents={mockAgents} onSubmit={onSubmit} />);

    const requirementsInput = screen.getByRole("textbox", { name: /requirements/i });
    fireEvent.change(requirementsInput, { target: { value: "Build something" } });

    const submitButton = screen.getByRole("button", { name: /submit/i });
    expect(submitButton).toBeDisabled();
  });

  it("submit button is disabled when isSubmitting is true", () => {
    const onSubmit = jest.fn();
    render(
      <TaskForm
        agents={mockAgents}
        onSubmit={onSubmit}
        isSubmitting={true}
        initialValues={{
          project_type: "new",
          project_name: "Test Project",
          agent_id: "agent-1",
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
        agents={mockAgents}
        onSubmit={onSubmit}
        initialValues={{
          project_type: "new",
          project_name: "My Project",
          agent_id: "agent-1",
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
          agent_id: "agent-1",
        })
      );
    });
  });
});
