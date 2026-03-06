"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { pushTaskToRemote } from "@/client/sdk.gen";
import type { PushResponse } from "@/client/types.gen";

interface PushToRemoteButtonProps {
  taskId: string;
  projectGitUrl?: string | null;
}

export function PushToRemoteButton({ taskId, projectGitUrl }: PushToRemoteButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<PushResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [gitUrlInput, setGitUrlInput] = useState<string>("");

  const handlePush = async () => {
    const urlOverride = projectGitUrl ? undefined : gitUrlInput.trim() || undefined;
    if (!projectGitUrl && !urlOverride) {
      setError("Please enter a Git URL before pushing.");
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response = await pushTaskToRemote({
        path: { task_id: taskId },
        body: urlOverride ? { git_url: urlOverride } : undefined,
      });
      if (response.data) {
        setResult(response.data);
      } else {
        const err = response.error as { detail?: string } | undefined;
        setError(err?.detail ?? "Push failed: no response data");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Push failed");
    } finally {
      setIsLoading(false);
    }
  };

  if (result) {
    return (
      <div className="p-3 bg-green-50 border border-green-200 rounded-md text-sm text-green-800">
        ✓ Pushed to branch <span className="font-mono font-medium">{result.branch_name}</span>{" "}
        → <span className="font-mono text-xs">{result.remote_url}</span>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {!projectGitUrl && (
        <div className="space-y-1">
          <label
            htmlFor="push-git-url-input"
            className="block text-sm font-medium text-foreground"
          >
            Git URL <span className="text-red-500">*</span>
          </label>
          <Input
            id="push-git-url-input"
            aria-label="Git URL for push"
            placeholder="https://github.com/org/repo.git"
            value={gitUrlInput}
            onChange={(e) => setGitUrlInput(e.target.value)}
          />
        </div>
      )}
      <Button onClick={handlePush} disabled={isLoading} variant="default">
        {isLoading ? "Pushing..." : "Push to Remote"}
      </Button>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
