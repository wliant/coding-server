"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface GeneralSettingsProps {
  initialSettings: Record<string, string>;
  onSave: (settings: Record<string, string>) => Promise<void>;
}

export function GeneralSettings({
  initialSettings,
  onSave,
}: GeneralSettingsProps) {
  const [workPath, setWorkPath] = useState(
    initialSettings["agent.work.path"] ?? ""
  );
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasChanges = workPath !== (initialSettings["agent.work.path"] ?? "");

  const handleSave = async () => {
    if (!hasChanges || isSaving) return;
    setIsSaving(true);
    setError(null);
    setSaveSuccess(false);
    try {
      await onSave({ "agent.work.path": workPath });
      setSaveSuccess(true);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to save settings"
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setWorkPath(initialSettings["agent.work.path"] ?? "");
    setSaveSuccess(false);
    setError(null);
  };

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <label
          htmlFor="agent-work-path"
          className="block text-sm font-medium text-foreground"
        >
          Agent Working Directory
        </label>
        <p className="text-xs text-muted-foreground">
          Working directory used by the agent
        </p>
        <Input
          id="agent-work-path"
          type="text"
          value={workPath}
          onChange={(e) => {
            setWorkPath(e.target.value);
            setSaveSuccess(false);
          }}
          placeholder="/path/to/working/directory"
        />
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
        <Button
          onClick={handleSave}
          disabled={!hasChanges || isSaving}
        >
          {isSaving ? "Saving..." : "Save"}
        </Button>
        <Button
          variant="outline"
          onClick={handleCancel}
          disabled={isSaving}
        >
          Cancel
        </Button>
      </div>
    </div>
  );
}
