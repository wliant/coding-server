"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { pushTaskToRemote } from "@/client/sdk.gen";
import type { PushResponse } from "@/client/types.gen";

interface PushToRemoteButtonProps {
  taskId: string;
}

export function PushToRemoteButton({ taskId }: PushToRemoteButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<PushResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handlePush = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await pushTaskToRemote({ path: { task_id: taskId } });
      if (response.data) {
        setResult(response.data);
      } else {
        setError("Push failed: no response data");
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
      <Button
        onClick={handlePush}
        disabled={isLoading}
        variant="default"
      >
        {isLoading ? "Pushing..." : "Push to Remote"}
      </Button>
      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}
    </div>
  );
}
