import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AgentSettings } from "@/components/settings/AgentSettings";

const defaultSettings: Record<string, string> = {
  "agent.simple_crewai.llm_provider": "ollama",
  "agent.simple_crewai.llm_model": "qwen2.5-coder:7b",
  "agent.simple_crewai.llm_temperature": "0.2",
  "agent.simple_crewai.ollama_base_url": "http://localhost:11434",
  "agent.simple_crewai.openai_api_key": "",
  "agent.simple_crewai.anthropic_api_key": "",
};

describe("AgentSettings — temperature validation", () => {
  it("shows error and does not call onSave when temperature is '-1'", async () => {
    const onSave = jest.fn();
    render(<AgentSettings initialSettings={defaultSettings} onSave={onSave} />);

    const tempInput = screen.getByPlaceholderText("0.2");
    await userEvent.clear(tempInput);
    await userEvent.type(tempInput, "-1");

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    expect(screen.getByText(/must be between 0\.0 and 2\.0/i)).toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();
  });

  it("shows error and does not call onSave when temperature is '2.1'", async () => {
    const onSave = jest.fn();
    render(<AgentSettings initialSettings={defaultSettings} onSave={onSave} />);

    const tempInput = screen.getByPlaceholderText("0.2");
    await userEvent.clear(tempInput);
    await userEvent.type(tempInput, "2.1");

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    expect(screen.getByText(/must be between 0\.0 and 2\.0/i)).toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();
  });

  it("shows error and does not call onSave when temperature is 'abc'", async () => {
    const onSave = jest.fn();
    render(<AgentSettings initialSettings={defaultSettings} onSave={onSave} />);

    const tempInput = screen.getByPlaceholderText("0.2");
    await userEvent.clear(tempInput);
    await userEvent.type(tempInput, "abc");

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    expect(screen.getByText(/must be a number/i)).toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();
  });

  it("calls onSave when temperature is '0.5'", async () => {
    const onSave = jest.fn().mockResolvedValue(undefined);
    render(<AgentSettings initialSettings={defaultSettings} onSave={onSave} />);

    const tempInput = screen.getByPlaceholderText("0.2");
    await userEvent.clear(tempInput);
    await userEvent.type(tempInput, "0.5");

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => expect(onSave).toHaveBeenCalled());
  });

  it("calls onSave when temperature is '0.0'", async () => {
    const onSave = jest.fn().mockResolvedValue(undefined);
    render(<AgentSettings initialSettings={defaultSettings} onSave={onSave} />);

    const tempInput = screen.getByPlaceholderText("0.2");
    await userEvent.clear(tempInput);
    await userEvent.type(tempInput, "0.0");

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => expect(onSave).toHaveBeenCalled());
  });

  it("calls onSave when temperature is '2.0'", async () => {
    const onSave = jest.fn().mockResolvedValue(undefined);
    render(<AgentSettings initialSettings={defaultSettings} onSave={onSave} />);

    const tempInput = screen.getByPlaceholderText("0.2");
    await userEvent.clear(tempInput);
    await userEvent.type(tempInput, "2.0");

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => expect(onSave).toHaveBeenCalled());
  });
});

describe("AgentSettings — API key masking", () => {
  it("shows masked placeholder when stored openai_api_key is non-empty", () => {
    const settings = { ...defaultSettings, "agent.simple_crewai.openai_api_key": "sk-real-key" };
    render(<AgentSettings initialSettings={settings} onSave={jest.fn()} />);

    const inputs = screen.getAllByDisplayValue("••••••••");
    expect(inputs.length).toBeGreaterThanOrEqual(1);
  });

  it("shows empty field when stored openai_api_key is empty", () => {
    render(<AgentSettings initialSettings={defaultSettings} onSave={jest.fn()} />);

    // API key fields should be empty (no placeholder shown) when value is empty
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    passwordInputs.forEach((input) => {
      expect((input as HTMLInputElement).value).toBe("");
    });
  });
});
