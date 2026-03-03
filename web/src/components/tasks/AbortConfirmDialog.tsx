"use client";

import React from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface AbortConfirmDialogProps {
  open: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export function AbortConfirmDialog({
  open,
  onConfirm,
  onCancel,
  isLoading = false,
}: AbortConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(isOpen: boolean) => !isOpen && onCancel()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Abort Task</DialogTitle>
          <DialogDescription>
            Are you sure you want to abort this task? This action cannot be
            undone unless you resubmit the task.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={onCancel} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={isLoading}
          >
            {isLoading ? "Aborting..." : "Confirm Abort"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
