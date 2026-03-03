"use client";

import React, { useEffect, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { GeneralSettings } from "@/components/settings/GeneralSettings";
import { getSettingsSettingsGet, updateSettingsSettingsPut } from "@/client/sdk.gen";
import { client } from "@/client/client.gen";

// Configure the client base URL
client.setConfig({ baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000" });

export default function SettingsPage() {
  const [settings, setSettings] = useState<Record<string, string>>({
    "agent.work.path": "",
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
      setSettings(result.data.settings);
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

      <Tabs defaultValue="general">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
        </TabsList>
        <TabsContent value="general" className="mt-6">
          <GeneralSettings initialSettings={settings} onSave={handleSave} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
