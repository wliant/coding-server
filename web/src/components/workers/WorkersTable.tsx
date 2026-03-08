"use client";

import React from "react";
import Link from "next/link";
import type { WorkerStatus } from "@/client/types.gen";

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    free: "bg-green-100 text-green-800",
    in_progress: "bg-blue-100 text-blue-800",
    completed: "bg-gray-100 text-gray-800",
    failed: "bg-red-100 text-red-800",
    unreachable: "bg-orange-100 text-orange-800",
  };
  const cls = colors[status] ?? "bg-gray-100 text-gray-600";
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {status.replace("_", " ")}
    </span>
  );
}

function relativeTime(isoString: string): string {
  const date = new Date(isoString);
  const diffMs = Date.now() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  return `${diffHr}h ago`;
}

interface WorkersTableProps {
  workers: WorkerStatus[];
}

export function WorkersTable({ workers }: WorkersTableProps) {
  if (workers.length === 0) {
    return (
      <p className="text-muted-foreground text-sm">
        No workers registered. Start a worker service to see it here.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-md border">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Worker ID</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Agent Type</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Current Task</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Last Heartbeat</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {workers.map((w) => (
            <tr key={w.worker_id}>
              <td className="px-4 py-3 font-mono text-xs text-gray-500">
                {w.worker_id.slice(0, 8)}&hellip;
              </td>
              <td className="px-4 py-3 text-gray-700">{w.agent_type}</td>
              <td className="px-4 py-3">
                <StatusBadge status={w.status} />
              </td>
              <td className="px-4 py-3">
                {w.current_task_id ? (
                  <Link
                    href={`/tasks/${w.current_task_id}`}
                    className="font-mono text-xs text-blue-600 hover:underline"
                  >
                    {w.current_task_id.slice(0, 8)}&hellip;
                  </Link>
                ) : (
                  <span className="text-gray-400">—</span>
                )}
              </td>
              <td className="px-4 py-3 text-gray-500">
                {relativeTime(w.last_heartbeat_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
