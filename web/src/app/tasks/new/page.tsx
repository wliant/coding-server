"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { TaskForm, type TaskFormValues } from "@/components/tasks/TaskForm";
import { listAgents, createTaskTasksPost } from "@/client/sdk.gen";
import type { AgentResponse } from "@/client/types.gen";
import { client } from "@/client/client.gen";

client.setConfig({ baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000" });

export default function NewTaskPage() {
  const router = useRouter();
  const [agents, setAgents] = useState<AgentResponse[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listAgents().then((result) => {
      if (result.data) setAgents(result.data);
    });
  }, []);

  const handleSubmit = async (data: TaskFormValues) => {
    setIsSubmitting(true);
    setError(null);
    try {
      const result = await createTaskTasksPost({
        body: {
          task_type: data.task_type,
          project_name: data.project_name ?? null,
          agent_id: data.agent_id,
          git_url: data.git_url ?? null,
          branch: data.branch ?? null,
          requirements: data.requirements,
          commits_to_review: data.commits_to_review ?? null,
        },
      });

      if (result.data) {
        router.push("/tasks");
      } else {
        const err = result.error as { detail?: string | Array<{ msg: string }> } | undefined;
        if (err?.detail) {
          if (Array.isArray(err.detail)) {
            setError(err.detail.map((d) => d.msg).join("; "));
          } else {
            setError(err.detail);
          }
        } else {
          setError("Failed to create task. Please try again.");
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">Submit New Task</h1>
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md text-red-700">
          {error}
        </div>
      )}
      <TaskForm agents={agents} onSubmit={handleSubmit} isSubmitting={isSubmitting} />
    </div>
  );
}
