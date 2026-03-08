"use client";

import React, { useEffect, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AgentSettings } from "@/components/settings/AgentSettings";
import { GitHubSettings } from "@/components/settings/GitHubSettings";
import { getSettingsSettingsGet, updateSettingsSettingsPut } from "@/client/sdk.gen";
import { client } from "@/client/client.gen";

// Configure the client base URL
client.setConfig({ baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000" });

export default function SettingsPage() {
  const [settings, setSettings] = useState<Record<string, string>>({
    "agent.simple_crewai.llm_provider": "ollama",
    "agent.simple_crewai.llm_model": "qwen2.5-coder:7b",
    "agent.simple_crewai.llm_temperature": "0.2",
    "agent.simple_crewai.ollama_base_url": "http://localhost:11434",
    "agent.simple_crewai.openai_api_key": "",
    "agent.simple_crewai.anthropic_api_key": "",
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSettingsSettingsGet()
      .then((result) => {
        if (result.data) {
          setSettings(result.data.settings);
        }
      })
      .catch((err) => {
        setError(
          err instanceof Error ? err.message : "Failed to load settings"
        );
      })
      .finally(() => setIsLoading(false));
  }, []);

  const handleSave = async (updatedSettings: Record<string, string>) => {
    const result = await updateSettingsSettingsPut({
      body: { settings: updatedSettings },
    });
    if (result.data) {
      setSettings((prev) => ({ ...prev, ...result.data!.settings }));
    }
  };

  if (isLoading) {
    return <p className="text-muted-foreground">Loading settings...</p>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md text-red-700">
          {error}
        </div>
      )}

      <Tabs defaultValue="agent">
        <TabsList>
          <TabsTrigger value="agent">Agent Settings</TabsTrigger>
          <TabsTrigger value="github">GitHub</TabsTrigger>
        </TabsList>
        <TabsContent value="agent" className="mt-6">
          <AgentSettings initialSettings={settings} onSave={handleSave} />
        </TabsContent>
        <TabsContent value="github" className="mt-6">
          <GitHubSettings initialSettings={settings} onSave={handleSave} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
