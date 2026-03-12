"use client";

import React, { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { TaskForm, type TaskFormValues } from "@/components/tasks/TaskForm";
import { listAgents, listTasksTasksGet, updateTaskTasksTaskIdPatch } from "@/client/sdk.gen";
import { client } from "@/client/client.gen";
import type { AgentResponse, TaskResponse } from "@/client/types.gen";

client.setConfig({ baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000" });

export default function EditTaskPage() {
  const router = useRouter();
  const params = useParams();
  const taskId = params.id as string;

  const [task, setTask] = useState<TaskResponse | null>(null);
  const [agents, setAgents] = useState<AgentResponse[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [tasksResult, agentsResult] = await Promise.all([
          listTasksTasksGet(),
          listAgents(),
        ]);

        if (tasksResult.data) {
          const found = tasksResult.data.find((t) => t.id === taskId);
          if (!found || found.status !== "aborted") {
            router.push("/tasks");
            return;
          }
          setTask(found);
        }

        if (agentsResult.data) setAgents(agentsResult.data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load task data");
      } finally {
        setIsLoading(false);
      }
    };
    loadData();
  }, [taskId, router]);

  const handleSubmit = async (data: TaskFormValues) => {
    if (!task) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const result = await updateTaskTasksTaskIdPatch({
        path: { task_id: task.id },
        body: { status: "pending", requirements: data.requirements },
      });
      if (result.data) {
        router.push("/tasks");
      } else {
        setError("Failed to resubmit task. Please try again.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) return <p className="text-muted-foreground">Loading task...</p>;
  if (!task) return null;

  const initialValues: TaskFormValues = {
    task_type: task.task_type,
    project_name: task.project.name ?? "",
    agent_id: task.agent?.id ?? "",
    git_url: task.project.git_url ?? "",
    requirements: task.requirements,
  };

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">Edit Task</h1>
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md text-red-700">
          {error}
        </div>
      )}
      <TaskForm
        agents={agents}
        onSubmit={handleSubmit}
        initialValues={initialValues}
        isSubmitting={isSubmitting}
      />
    </div>
  );
}
