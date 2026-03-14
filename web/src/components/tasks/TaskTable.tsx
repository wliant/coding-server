"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "./StatusBadge";
import { AbortConfirmDialog } from "./AbortConfirmDialog";
import { EmptyState } from "./EmptyState";
import { updateTaskTasksTaskIdPatch } from "@/client/sdk.gen";
import { client } from "@/client/client.gen";
import type { TaskResponse } from "@/client/types.gen";
import { TASK_TYPE_LABELS } from "@/lib/task-type-labels";

// Configure the client base URL
client.setConfig({ baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000" });

interface TaskTableProps {
  tasks: TaskResponse[];
}

export function TaskTable({ tasks: initialTasks }: TaskTableProps) {
  const [tasks, setTasks] = useState<TaskResponse[]>(initialTasks);
  const [search, setSearch] = useState("");
  const [abortingTaskId, setAbortingTaskId] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [isAborting, setIsAborting] = useState(false);

  const getProjectLabel = (project: TaskResponse["project"]) => {
    if (project.name) return project.name;
    if (project.git_url) {
      const match = project.git_url.match(/\/([^/]+?)(?:\.git)?$/);
      return match ? match[1] : project.git_url;
    }
    return "New Project";
  };

  const filteredTasks = tasks.filter((task) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    const reqMatch = task.requirements.toLowerCase().includes(q);
    const nameMatch = getProjectLabel(task.project).toLowerCase().includes(q);
    return reqMatch || nameMatch;
  });

  const handleAbortClick = (taskId: string) => {
    setAbortingTaskId(taskId);
    setDialogOpen(true);
  };

  const handleAbortCancel = () => {
    setDialogOpen(false);
    setAbortingTaskId(null);
  };

  const handleAbortConfirm = async () => {
    if (!abortingTaskId) return;
    setIsAborting(true);
    try {
      const result = await updateTaskTasksTaskIdPatch({
        path: { task_id: abortingTaskId },
        body: { status: "aborted" },
      });
      if (result.data) {
        setTasks((prev) =>
          prev.map((t) =>
            t.id === abortingTaskId
              ? { ...t, status: "aborted" as const }
              : t
          )
        );
      }
    } catch (err) {
      console.error("Failed to abort task:", err);
    } finally {
      setIsAborting(false);
      setDialogOpen(false);
      setAbortingTaskId(null);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (tasks.length === 0) {
    return (
      <EmptyState
        message="No tasks yet."
        showSubmitLink={true}
      />
    );
  }

  return (
    <div className="space-y-4">
      <Input
        placeholder="Search tasks..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="max-w-sm"
      />

      {filteredTasks.length === 0 ? (
        <EmptyState message="No tasks match your search." />
      ) : (
        <div className="rounded-md border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="px-4 py-3 text-left font-medium">Project</th>
                <th className="px-4 py-3 text-left font-medium">Type</th>
                <th className="px-4 py-3 text-left font-medium">Agent</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
                <th className="px-4 py-3 text-left font-medium">Submitted</th>
                <th className="px-4 py-3 text-left font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredTasks.map((task) => (
                <tr key={task.id} className="border-b hover:bg-muted/25">
                  <td className="px-4 py-3">
                    <Link href={`/tasks/${task.id}`} className="block hover:underline">
                      <div className="font-medium">
                        {getProjectLabel(task.project)}
                      </div>
                      <div className="text-xs text-muted-foreground truncate max-w-xs">
                        {task.requirements}
                      </div>
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-block px-2 py-0.5 text-xs font-medium rounded-full bg-muted text-muted-foreground">
                      {TASK_TYPE_LABELS[task.task_type] ?? task.task_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {task.agent?.display_name ?? "—"}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={task.status} />
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {formatDate(task.created_at)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {task.status === "pending" && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleAbortClick(task.id)}
                        >
                          Abort
                        </Button>
                      )}
                      {task.status === "aborted" && (
                        <Link href={`/tasks/${task.id}/edit`}>
                          <Button variant="outline" size="sm">
                            Edit
                          </Button>
                        </Link>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <AbortConfirmDialog
        open={dialogOpen}
        onConfirm={handleAbortConfirm}
        onCancel={handleAbortCancel}
        isLoading={isAborting}
      />
    </div>
  );
}
