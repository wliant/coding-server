"use client";

import React from "react";
import type { SandboxStatus } from "@/client/types.gen";

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    free: "bg-green-100 text-green-800",
    allocated: "bg-blue-100 text-blue-800",
    unavailable: "bg-orange-100 text-orange-800",
    unreachable: "bg-red-100 text-red-800",
  };
  const cls = colors[status] ?? "bg-gray-100 text-gray-600";
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {status.replace("_", " ")}
    </span>
  );
}

function LabelPill({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700 mr-1">
      {label}
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

interface SandboxesTableProps {
  sandboxes: SandboxStatus[];
}

export function SandboxesTable({ sandboxes }: SandboxesTableProps) {
  if (sandboxes.length === 0) {
    return (
      <p className="text-muted-foreground text-sm">
        No sandboxes registered. Start a sandbox service to see it here.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-md border">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Sandbox ID</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Labels</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">URL</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Last Heartbeat</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {sandboxes.map((s) => (
            <tr key={s.sandbox_id}>
              <td className="px-4 py-3 font-mono text-xs text-gray-500">
                {s.sandbox_id.length > 12
                  ? `${s.sandbox_id.slice(0, 12)}...`
                  : s.sandbox_id}
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={s.status} />
              </td>
              <td className="px-4 py-3">
                {s.labels && s.labels.length > 0 ? (
                  s.labels.map((label) => <LabelPill key={label} label={label} />)
                ) : (
                  <span className="text-gray-400">—</span>
                )}
              </td>
              <td className="px-4 py-3 font-mono text-xs text-gray-500">
                {s.sandbox_url}
              </td>
              <td className="px-4 py-3 text-gray-500">
                {relativeTime(s.last_heartbeat_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
