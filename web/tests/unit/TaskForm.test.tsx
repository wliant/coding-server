import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import { TaskForm } from "../../src/components/tasks/TaskForm";
import type { AgentResponse } from "../../src/client/types.gen";

const mockAgents: AgentResponse[] = [
  { id: "agent-1", identifier: "simple_crewai_pair_agent", display_name: "CrewAI Pair Agent", is_active: true },
  { id: "agent-2", identifier: "openhands_agent", display_name: "OpenHands Agent", is_active: true },
];

describe("TaskForm", () => {
  it("renders task type select, agent select, and requirements textarea", () => {
    const onSubmit = jest.fn();
    render(<TaskForm agents={mockAgents} onSubmit={onSubmit} />);

    expect(screen.getByLabelText(/task type/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^agent$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/feature description/i)).toBeInTheDocument();
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

    const requirementsInput = screen.getByLabelText(/feature description/i);
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
          task_type: "build_feature",
          agent_id: "agent-1",
          git_url: "https://github.com/org/repo.git",
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
          task_type: "build_feature",
          agent_id: "agent-1",
          git_url: "https://github.com/org/repo.git",
          requirements: "",
        }}
      />
    );

    const requirementsInput = screen.getByLabelText(/feature description/i);
    await userEvent.type(requirementsInput, "Build a REST API");

    const submitButton = screen.getByRole("button", { name: /submit/i });
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          requirements: "Build a REST API",
          agent_id: "agent-1",
          task_type: "build_feature",
        })
      );
    });
  });
});
