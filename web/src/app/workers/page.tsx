"use client";

import React, { useCallback, useEffect, useState } from "react";
import { WorkersTable } from "@/components/workers/WorkersTable";
import { listWorkersWorkersGet } from "@/client/sdk.gen";
import { client } from "@/client/client.gen";
import type { WorkerStatus } from "@/client/types.gen";
import { Button } from "@/components/ui/button";

client.setConfig({ baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000" });

const REFRESH_INTERVAL_MS = 15_000;

export default function WorkersPage() {
  const [workers, setWorkers] = useState<WorkerStatus[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const fetchWorkers = useCallback(() => {
    listWorkersWorkersGet()
      .then((result) => {
        if (result.data) {
          setWorkers(result.data);
          setError(null);
        }
      })
      .catch((err) => {
        setError(
          err instanceof Error ? err.message : "Unable to reach controller"
        );
      })
      .finally(() => {
        setIsLoading(false);
        setLastRefreshed(new Date());
      });
  }, []);

  useEffect(() => {
    fetchWorkers();
    const interval = setInterval(fetchWorkers, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchWorkers]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Workers</h1>
          {lastRefreshed && (
            <p className="text-xs text-gray-400 mt-1">
              Last refreshed: {lastRefreshed.toLocaleTimeString()} · auto-refreshes every 15s
            </p>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={fetchWorkers}>
          Refresh
        </Button>
      </div>

      {isLoading ? (
        <p className="text-muted-foreground">Loading workers...</p>
      ) : error ? (
        <div className="p-4 bg-orange-50 border border-orange-200 rounded-md text-orange-700">
          <p className="font-medium">Controller unavailable</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      ) : (
        <WorkersTable workers={workers} />
      )}
    </div>
  );
}
