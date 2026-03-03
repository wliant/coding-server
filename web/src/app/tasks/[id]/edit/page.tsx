"use client";

import React, { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { TaskForm, type TaskFormValues } from "@/components/tasks/TaskForm";
import {
  listTasksTasksGet,
  listProjectsProjectsGet,
  updateTaskTasksTaskIdPatch,
} from "@/client/sdk.gen";
import { client } from "@/client/client.gen";
import type { TaskResponse, ProjectSummary } from "@/client/types.gen";

// Configure the client base URL
client.setConfig({ baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000" });

export default function EditTaskPage() {
  const router = useRouter();
  const params = useParams();
  const taskId = params.id as string;

  const [task, setTask] = useState<TaskResponse | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [tasksResult, projectsResult] = await Promise.all([
          listTasksTasksGet(),
          listProjectsProjectsGet(),
        ]);

        if (tasksResult.data) {
          const found = tasksResult.data.find((t) => t.id === taskId);
          if (!found) {
            router.push("/tasks");
            return;
          }
          if (found.status !== "aborted") {
            router.push("/tasks");
            return;
          }
          setTask(found);
        }

        if (projectsResult.data) {
          setProjects(projectsResult.data);
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load task data"
        );
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
        body: {
          status: "pending",
          requirements: data.requirements,
          dev_agent_type: data.dev_agent_type as "spec_driven_development",
          test_agent_type: data.test_agent_type as "generic_testing",
          project_id: data.project_id ?? null,
        },
      });

      if (result.data) {
        router.push("/tasks");
      } else {
        setError("Failed to resubmit task. Please try again.");
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "An unexpected error occurred"
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return <p className="text-muted-foreground">Loading task...</p>;
  }

  if (!task) {
    return null;
  }

  const initialValues: TaskFormValues = {
    project_type:
      task.project.name === null ? "new" : "existing",
    project_id: task.project.name !== null ? task.project.id : undefined,
    dev_agent_type: task.dev_agent_type,
    test_agent_type: task.test_agent_type,
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
        projects={projects}
        onSubmit={handleSubmit}
        initialValues={initialValues}
        isSubmitting={isSubmitting}
      />
    </div>
  );
}
