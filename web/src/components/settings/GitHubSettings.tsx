"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const GITHUB_TOKEN_KEY = "github.token";
const API_KEY_PLACEHOLDER = "••••••••";

interface GitHubSettingsProps {
  initialSettings: Record<string, string>;
  onSave: (settings: Record<string, string>) => Promise<void>;
}

export function GitHubSettings({ initialSettings, onSave }: GitHubSettingsProps) {
  const [tokenInput, setTokenInput] = useState(
    initialSettings[GITHUB_TOKEN_KEY] ? API_KEY_PLACEHOLDER : ""
  );

  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    if (isSaving) return;

    setIsSaving(true);
    setError(null);
    setSaveSuccess(false);

    try {
      // Only include the token if the user changed it (not still showing placeholder)
      if (tokenInput !== API_KEY_PLACEHOLDER) {
        await onSave({ [GITHUB_TOKEN_KEY]: tokenInput });
      }
      setSaveSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setTokenInput(initialSettings[GITHUB_TOKEN_KEY] ? API_KEY_PLACEHOLDER : "");
    setSaveSuccess(false);
    setError(null);
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-semibold text-foreground mb-4">GitHub</h3>

        <div className="space-y-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-foreground">
              Personal Access Token
            </label>
            <p className="text-xs text-muted-foreground">
              Used to authenticate HTTPS clone and push operations. Requires{" "}
              <code className="font-mono">repo</code> scope.
            </p>
            <Input
              type="password"
              value={tokenInput}
              onChange={(e) => {
                setTokenInput(e.target.value);
                setSaveSuccess(false);
              }}
              placeholder="ghp_..."
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
