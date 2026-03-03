"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { TaskTable } from "@/components/tasks/TaskTable";
import { listTasksTasksGet } from "@/client/sdk.gen";
import { client } from "@/client/client.gen";
import type { TaskResponse } from "@/client/types.gen";

// Configure the client base URL
client.setConfig({ baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000" });

export default function TasksPage() {
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTasksTasksGet()
      .then((result) => {
        if (result.data) {
          setTasks(result.data);
        }
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load tasks");
      })
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Tasks</h1>
        <Button asChild>
          <Link href="/tasks/new">Submit Task</Link>
        </Button>
      </div>

      {isLoading ? (
        <p className="text-muted-foreground">Loading tasks...</p>
      ) : error ? (
        <div className="p-4 bg-red-50 border border-red-200 rounded-md text-red-700">
          {error}
        </div>
      ) : (
        <TaskTable tasks={tasks} />
      )}
    </div>
  );
}
