import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import { GeneralSettings } from "../../src/components/settings/GeneralSettings";

const mockInitialSettings = {
  "agent.work.path": "/home/user/work",
};

describe("GeneralSettings", () => {
  it("renders agent.work.path input with label 'Agent Working Directory'", () => {
    const onSave = jest.fn();
    render(
      <GeneralSettings
        initialSettings={mockInitialSettings}
        onSave={onSave}
      />
    );

    expect(screen.getByLabelText(/agent working directory/i)).toBeInTheDocument();
    expect(screen.getByDisplayValue("/home/user/work")).toBeInTheDocument();
  });

  it("Save button is disabled when value is unchanged from initial", () => {
    const onSave = jest.fn();
    render(
      <GeneralSettings
        initialSettings={mockInitialSettings}
        onSave={onSave}
      />
    );

    const saveButton = screen.getByRole("button", { name: /save/i });
    expect(saveButton).toBeDisabled();
  });

  it("Save button is enabled when value changes", async () => {
    const onSave = jest.fn();
    render(
      <GeneralSettings
        initialSettings={mockInitialSettings}
        onSave={onSave}
      />
    );

    const input = screen.getByLabelText(/agent working directory/i);
    await userEvent.clear(input);
    await userEvent.type(input, "/new/path");

    const saveButton = screen.getByRole("button", { name: /save/i });
    expect(saveButton).not.toBeDisabled();
  });

  it("calls onSave callback with updated value on submit", async () => {
    const onSave = jest.fn().mockResolvedValue(undefined);
    render(
      <GeneralSettings
        initialSettings={mockInitialSettings}
        onSave={onSave}
      />
    );

    const input = screen.getByLabelText(/agent working directory/i);
    await userEvent.clear(input);
    await userEvent.type(input, "/new/path");

    const saveButton = screen.getByRole("button", { name: /save/i });
    await userEvent.click(saveButton);

    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith(
        expect.objectContaining({
          "agent.work.path": "/new/path",
        })
      );
    });
  });

  it("Cancel button reverts unsaved changes", async () => {
    const onSave = jest.fn();
    render(
      <GeneralSettings
        initialSettings={mockInitialSettings}
        onSave={onSave}
      />
    );

    const input = screen.getByLabelText(/agent working directory/i);
    await userEvent.clear(input);
    await userEvent.type(input, "/new/path");

    const cancelButton = screen.getByRole("button", { name: /cancel/i });
    await userEvent.click(cancelButton);

    expect(screen.getByDisplayValue("/home/user/work")).toBeInTheDocument();
  });

  it("shows success message after save", async () => {
    const onSave = jest.fn().mockResolvedValue(undefined);
    render(
      <GeneralSettings
        initialSettings={mockInitialSettings}
        onSave={onSave}
      />
    );

    const input = screen.getByLabelText(/agent working directory/i);
    await userEvent.clear(input);
    await userEvent.type(input, "/new/path");

    const saveButton = screen.getByRole("button", { name: /save/i });
    await userEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText(/saved/i)).toBeInTheDocument();
    });
  });
});
