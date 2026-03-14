"use client";

import React, { useEffect, useState } from "react";
import { DiffViewer } from "@/components/tasks/DiffViewer";
import {
  getWorkerBaseUrl,
  fetchDiffList,
  fetchFileDiff,
  type DiffFileEntry,
  type FileDiffResponse,
} from "@/lib/workerClient";

interface DiffTabProps {
  taskId: string;
  workerUrl: string | null | undefined;
}

export function DiffTab({ taskId, workerUrl }: DiffTabProps) {
  const baseUrl = getWorkerBaseUrl(workerUrl);

  const [diffFiles, setDiffFiles] = useState<DiffFileEntry[]>([]);
  const [diffLoading, setDiffLoading] = useState(true);
  const [diffError, setDiffError] = useState<string | null>(null);
  const [selectedDiffPath, setSelectedDiffPath] = useState<string | null>(null);
  const [fileDiff, setFileDiff] = useState<FileDiffResponse | null>(null);
  const [fileDiffLoading, setFileDiffLoading] = useState(false);
  const [fileDiffError, setFileDiffError] = useState<string | null>(null);

  useEffect(() => {
    if (!baseUrl) {
      setDiffLoading(false);
      setDiffError("Worker URL not available");
      return;
    }

    setDiffLoading(true);
    setDiffError(null);
    fetchDiffList(baseUrl, taskId)
      .then((data) => {
        setDiffFiles(data.changed_files);
        if (data.changed_files.length > 0) {
          setSelectedDiffPath(data.changed_files[0].path);
        }
      })
      .catch((err) => {
        setDiffError(err instanceof Error ? err.message : "Failed to load diff");
      })
      .finally(() => setDiffLoading(false));
  }, [baseUrl, taskId]);

  useEffect(() => {
    if (!selectedDiffPath || !baseUrl) return;

    setFileDiffLoading(true);
    setFileDiffError(null);
    setFileDiff(null);
    fetchFileDiff(baseUrl, taskId, selectedDiffPath)
      .then((data) => setFileDiff(data))
      .catch((err) => {
        setFileDiffError(
          err instanceof Error ? err.message : "Failed to load file diff"
        );
      })
      .finally(() => setFileDiffLoading(false));
  }, [selectedDiffPath, baseUrl, taskId]);

  return (
    <div className="rounded-lg border">
      <div className="px-4 py-3 border-b">
        <h2 className="font-semibold text-sm">Changes</h2>
      </div>

      {diffError && !diffLoading && (
        <div className="p-4">
          <p className="text-sm text-red-600">{diffError}</p>
        </div>
      )}

      {!diffError && (
        <DiffViewer
          diffFiles={diffFiles}
          selectedPath={selectedDiffPath}
          onSelectFile={setSelectedDiffPath}
          fileDiff={fileDiff}
          isLoading={diffLoading || fileDiffLoading}
          error={fileDiffError}
        />
      )}
    </div>
  );
}
