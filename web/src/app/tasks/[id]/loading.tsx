import React from "react";

export default function TaskDetailLoading() {
  return (
    <div className="space-y-6 max-w-3xl animate-pulse">
      <div className="flex items-center gap-4">
        <div className="h-9 bg-muted rounded w-32" />
        <div className="h-8 bg-muted rounded w-36" />
      </div>

      <div className="rounded-lg border p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="h-4 bg-muted rounded w-72" />
          <div className="h-6 bg-muted rounded w-20" />
        </div>

        <div className="space-y-2">
          <div className="h-3 bg-muted rounded w-24" />
          <div className="h-4 bg-muted rounded w-full" />
          <div className="h-4 bg-muted rounded w-4/5" />
        </div>

        <div className="grid grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="space-y-1">
              <div className="h-3 bg-muted rounded w-20" />
              <div className="h-4 bg-muted rounded w-32" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
