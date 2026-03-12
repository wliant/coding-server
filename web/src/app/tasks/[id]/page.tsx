"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/tasks/StatusBadge";
import { PushToRemoteButton } from "@/components/tasks/PushToRemoteButton";
import { SourceCodeSection } from "@/components/tasks/SourceCodeSection";
import { initiateCleanupTasksTaskIdCleanupPost, getTaskDetail } from "@/client/sdk.gen";
import { client } from "@/client/client.gen";
import type { TaskDetailResponse, TaskType } from "@/client/types.gen";

client.setConfig({ baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000" });

const TASK_TYPE_LABELS: Record<TaskType, string> = {
  build_feature: "Build a Feature",
  fix_bug: "Fix a Bug",
  review_code: "Review Code",
  refactor_code: "Refactor Code",
  write_tests: "Write Tests",
  scaffold_project: "Scaffold a Project",
};

export default function TaskDetailPage() {
  const params = useParams();
  const taskId = params.id as string;

  const [task, setTask] = useState<TaskDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCleaningUp, setIsCleaningUp] = useState(false);
  const [cleanupError, setCleanupError] = useState<string | null>(null);

  useEffect(() => {
    if (!taskId) return;
    getTaskDetail({ path: { task_id: taskId } })
      .then((result) => {
        if (result.data) {
          setTask(result.data);
        } else {
          setError("Task not found");
        }
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load task");
      })
      .finally(() => setIsLoading(false));
  }, [taskId]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 bg-muted animate-pulse rounded w-48" />
        <div className="h-4 bg-muted animate-pulse rounded w-full" />
        <div className="h-4 bg-muted animate-pulse rounded w-3/4" />
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className="space-y-4">
        <Link href="/tasks">
          <Button variant="outline" size="sm">← Back to Tasks</Button>
        </Link>
        <div className="p-4 bg-red-50 border border-red-200 rounded-md text-red-700">
          {error ?? "Task not found"}
        </div>
      </div>
    );
  }

  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center gap-4">
        <Link href="/tasks">
          <Button variant="outline" size="sm">← Back to Tasks</Button>
        </Link>
        <h1 className="text-2xl font-bold">Task Detail</h1>
      </div>

      <div className="rounded-lg border p-6 space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground font-mono">{task.id}</span>
          <div className="flex items-center gap-2">
            <span className="inline-block px-2 py-0.5 text-xs font-medium rounded-full bg-muted text-muted-foreground">
              {TASK_TYPE_LABELS[task.task_type] ?? task.task_type}
            </span>
            <StatusBadge status={task.status} />
          </div>
        </div>

        <div>
          <p className="text-sm font-medium text-muted-foreground mb-1">Requirements</p>
          <p className="text-sm whitespace-pre-wrap">{task.requirements}</p>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="font-medium text-muted-foreground mb-1">Project</p>
            <p>{task.project.name ?? "New Project"}</p>
          </div>
          {task.project.git_url && (
            <div>
              <p className="font-medium text-muted-foreground mb-1">Git URL</p>
              <p className="font-mono text-xs truncate">{task.project.git_url}</p>
            </div>
          )}
          <div>
            <p className="font-medium text-muted-foreground mb-1">Submitted</p>
            <p>{formatDate(task.created_at)}</p>
          </div>
          {task.started_at && (
            <div>
              <p className="font-medium text-muted-foreground mb-1">Started</p>
              <p>{formatDate(task.started_at)}</p>
            </div>
          )}
          {task.completed_at && (
            <div>
              <p className="font-medium text-muted-foreground mb-1">Completed</p>
              <p>{formatDate(task.completed_at)}</p>
            </div>
          )}
          {task.commits_to_review != null && (
            <div>
              <p className="font-medium text-muted-foreground mb-1">Commits to Review</p>
              <p>{task.commits_to_review}</p>
            </div>
          )}
          {task.work_directory_path && (
            <div>
              <p className="font-medium text-muted-foreground mb-1">Working Directory</p>
              <p className="font-mono text-xs truncate">{task.work_directory_path}</p>
            </div>
          )}
        </div>

        {task.status === "in_progress" && task.elapsed_seconds != null && (
          <div className="p-3 bg-purple-50 border border-purple-200 rounded-md text-sm text-purple-800">
            ⏱ Running for {task.elapsed_seconds}s
          </div>
        )}

        {task.status === "failed" && task.error_message && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-800">
            <p className="font-medium mb-1">Error</p>
            <p className="whitespace-pre-wrap font-mono text-xs">{task.error_message}</p>
          </div>
        )}

        {task.status === "completed" && (
          <div className="pt-2 border-t">
            <PushToRemoteButton taskId={task.id} projectGitUrl={task.project.git_url} />
          </div>
        )}

        {(task.status === "completed" || task.status === "failed") && (
          <div className="pt-2 border-t space-y-2">
            {cleanupError && (
              <p className="text-sm text-red-600">{cleanupError}</p>
            )}
            <Button
              variant="outline"
              size="sm"
              disabled={isCleaningUp}
              onClick={async () => {
                setIsCleaningUp(true);
                setCleanupError(null);
                try {
                  await initiateCleanupTasksTaskIdCleanupPost({ path: { task_id: taskId } });
                  // Refresh task status
                  const result = await getTaskDetail({ path: { task_id: taskId } });
                  if (result.data) setTask(result.data);
                } catch (err) {
                  setCleanupError(
                    err instanceof Error ? err.message : "Cleanup failed"
                  );
                } finally {
                  setIsCleaningUp(false);
                }
              }}
            >
              {isCleaningUp ? "Cleaning up…" : "Clean Up"}
            </Button>
          </div>
        )}
      </div>

      {(task.status === "completed" || task.status === "failed") && (
        <SourceCodeSection
          taskId={String(task.id)}
          workerUrl={task.assigned_worker_url}
        />
      )}
    </div>
  );
}
