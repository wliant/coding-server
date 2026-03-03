"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { TaskForm, type TaskFormValues } from "@/components/tasks/TaskForm";
import { listProjectsProjectsGet, createTaskTasksPost } from "@/client/sdk.gen";
import type { ProjectSummary } from "@/client/types.gen";
import { client } from "@/client/client.gen";

// Configure the client base URL
client.setConfig({ baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000" });

export default function NewTaskPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listProjectsProjectsGet().then((result) => {
      if (result.data) {
        setProjects(result.data);
      }
    });
  }, []);

  const handleSubmit = async (data: TaskFormValues) => {
    setIsSubmitting(true);
    setError(null);
    try {
      const result = await createTaskTasksPost({
        body: {
          project_type: data.project_type,
          project_id: data.project_id ?? null,
          dev_agent_type: data.dev_agent_type as "spec_driven_development",
          test_agent_type: data.test_agent_type as "generic_testing",
          requirements: data.requirements,
        },
      });

      if (result.data) {
        router.push("/tasks");
      } else {
        setError("Failed to create task. Please try again.");
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
      <TaskForm
        projects={projects}
        onSubmit={handleSubmit}
        isSubmitting={isSubmitting}
      />
    </div>
  );
}
