import React from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  message: string;
  showSubmitLink?: boolean;
}

export function EmptyState({
  message,
  showSubmitLink = false,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <p className="text-muted-foreground text-lg mb-4">{message}</p>
      {showSubmitLink && (
        <Button asChild>
          <Link href="/tasks/new">Submit your first task</Link>
        </Button>
      )}
    </div>
  );
}
