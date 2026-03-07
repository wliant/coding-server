"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const PROVIDER_KEY = "agent.simple_crewai.llm_provider";
const MODEL_KEY = "agent.simple_crewai.llm_model";
const TEMPERATURE_KEY = "agent.simple_crewai.llm_temperature";
const OLLAMA_URL_KEY = "agent.simple_crewai.ollama_base_url";
const OPENAI_KEY = "agent.simple_crewai.openai_api_key";
const ANTHROPIC_KEY = "agent.simple_crewai.anthropic_api_key";

const API_KEY_PLACEHOLDER = "••••••••";

interface AgentSettingsProps {
  initialSettings: Record<string, string>;
  onSave: (settings: Record<string, string>) => Promise<void>;
}

function validateTemperature(value: string): string | null {
  const num = parseFloat(value);
  if (value.trim() === "" || isNaN(num)) {
    return "Temperature must be a number";
  }
  if (num < 0.0 || num > 2.0) {
    return "Temperature must be between 0.0 and 2.0";
  }
  return null;
}

export function AgentSettings({ initialSettings, onSave }: AgentSettingsProps) {
  const [provider, setProvider] = useState(
    initialSettings[PROVIDER_KEY] ?? "ollama"
  );
  const [model, setModel] = useState(initialSettings[MODEL_KEY] ?? "");
  const [temperature, setTemperature] = useState(
    initialSettings[TEMPERATURE_KEY] ?? "0.2"
  );
  const [ollamaUrl, setOllamaUrl] = useState(
    initialSettings[OLLAMA_URL_KEY] ?? ""
  );
  // API key fields: show masked placeholder if a value is stored
  const [openaiKey, setOpenaiKey] = useState(
    initialSettings[OPENAI_KEY] ? API_KEY_PLACEHOLDER : ""
  );
  const [anthropicKey, setAnthropicKey] = useState(
    initialSettings[ANTHROPIC_KEY] ? API_KEY_PLACEHOLDER : ""
  );

  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tempError, setTempError] = useState<string | null>(null);

  const handleSave = async () => {
    if (isSaving) return;

    const tempValidationError = validateTemperature(temperature);
    if (tempValidationError) {
      setTempError(tempValidationError);
      return;
    }
    setTempError(null);

    setIsSaving(true);
    setError(null);
    setSaveSuccess(false);

    try {
      const updates: Record<string, string> = {
        [PROVIDER_KEY]: provider,
        [MODEL_KEY]: model,
        [TEMPERATURE_KEY]: temperature,
        [OLLAMA_URL_KEY]: ollamaUrl,
      };

      // Only include API keys if the user changed them (not still showing placeholder)
      if (openaiKey !== API_KEY_PLACEHOLDER) {
        updates[OPENAI_KEY] = openaiKey;
      }
      if (anthropicKey !== API_KEY_PLACEHOLDER) {
        updates[ANTHROPIC_KEY] = anthropicKey;
      }

      await onSave(updates);
      setSaveSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setProvider(initialSettings[PROVIDER_KEY] ?? "ollama");
    setModel(initialSettings[MODEL_KEY] ?? "");
    setTemperature(initialSettings[TEMPERATURE_KEY] ?? "0.2");
    setOllamaUrl(initialSettings[OLLAMA_URL_KEY] ?? "");
    setOpenaiKey(initialSettings[OPENAI_KEY] ? API_KEY_PLACEHOLDER : "");
    setAnthropicKey(initialSettings[ANTHROPIC_KEY] ? API_KEY_PLACEHOLDER : "");
    setSaveSuccess(false);
    setError(null);
    setTempError(null);
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-semibold text-foreground mb-4">
          simple_crewai_pair_agent
        </h3>

        <div className="space-y-4">
          {/* LLM Provider */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-foreground">
              LLM Provider
            </label>
            <Select
              value={provider}
              onValueChange={(val) => {
                setProvider(val);
                setSaveSuccess(false);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select provider" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ollama">ollama</SelectItem>
                <SelectItem value="openai">openai</SelectItem>
                <SelectItem value="anthropic">anthropic</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Model */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-foreground">
              Model
            </label>
            <Input
              type="text"
              value={model}
              onChange={(e) => {
                setModel(e.target.value);
                setSaveSuccess(false);
              }}
              placeholder="e.g. qwen2.5-coder:7b"
            />
          </div>

          {/* Temperature */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-foreground">
              Temperature
            </label>
            <p className="text-xs text-muted-foreground">
              Decimal number between 0.0 and 2.0
            </p>
            <Input
              type="text"
              value={temperature}
              onChange={(e) => {
                setTemperature(e.target.value);
                setSaveSuccess(false);
                setTempError(null);
              }}
              placeholder="0.2"
            />
            {tempError && (
              <p className="text-xs text-red-600">{tempError}</p>
            )}
          </div>

          {/* Ollama Base URL */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-foreground">
              Ollama Base URL
            </label>
            <Input
              type="text"
              value={ollamaUrl}
              onChange={(e) => {
                setOllamaUrl(e.target.value);
                setSaveSuccess(false);
              }}
              placeholder="http://localhost:11434"
            />
          </div>

          {/* OpenAI API Key */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-foreground">
              OpenAI API Key
            </label>
            <Input
              type="password"
              value={openaiKey}
              onChange={(e) => {
                setOpenaiKey(e.target.value);
                setSaveSuccess(false);
              }}
              placeholder="sk-..."
            />
          </div>

          {/* Anthropic API Key */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-foreground">
              Anthropic API Key
            </label>
            <Input
              type="password"
              value={anthropicKey}
              onChange={(e) => {
                setAnthropicKey(e.target.value);
                setSaveSuccess(false);
              }}
              placeholder="sk-ant-..."
            />
          </div>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
          {error}
        </div>
      )}

      {saveSuccess && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-md text-green-700 text-sm">
          Settings saved successfully!
        </div>
      )}

      <div className="flex gap-3">
        <Button onClick={handleSave} disabled={isSaving}>
          {isSaving ? "Saving..." : "Save"}
        </Button>
        <Button variant="outline" onClick={handleCancel} disabled={isSaving}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
