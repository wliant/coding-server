import React from "react";
import { cn } from "@/lib/utils";
import type { TaskStatus } from "@/client/types.gen";

const statusConfig: Record<
  TaskStatus,
  { label: string; className: string }
> = {
  pending: {
    label: "Pending",
    className: "bg-blue-100 text-blue-800",
  },
  aborted: {
    label: "Aborted",
    className: "bg-yellow-100 text-yellow-800",
  },
  in_progress: {
    label: "In Progress",
    className: "bg-purple-100 text-purple-800",
  },
  completed: {
    label: "Completed",
    className: "bg-green-100 text-green-800",
  },
  failed: {
    label: "Failed",
    className: "bg-red-100 text-red-800",
  },
};

interface StatusBadgeProps {
  status: TaskStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const config = statusConfig[status] ?? {
    label: status,
    className: "bg-gray-100 text-gray-800",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        config.className
      )}
    >
      {config.label}
    </span>
  );
}
