"use client";

import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { FileTree } from "@/components/tasks/FileTree";
import { FileViewer } from "@/components/tasks/FileViewer";
import {
  getWorkerBaseUrl,
  fetchFileTree,
  fetchFileContent,
  type FileEntry,
} from "@/lib/workerClient";

interface SourceCodeSectionProps {
  taskId: string;
  workerUrl: string | null | undefined;
}

export function SourceCodeSection({
  taskId,
  workerUrl,
}: SourceCodeSectionProps) {
  const baseUrl = getWorkerBaseUrl(workerUrl);

  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>("");
  const [isBinary, setIsBinary] = useState(false);
  const [treeLoading, setTreeLoading] = useState(true);
  const [treeError, setTreeError] = useState<string | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);

  useEffect(() => {
    if (!baseUrl) {
      setTreeLoading(false);
      setTreeError("Worker URL not available");
      return;
    }

    setTreeLoading(true);
    fetchFileTree(baseUrl, taskId)
      .then((data) => {
        setEntries(data.entries);
        // Auto-select README or first file
        const files = data.entries.filter((e) => e.type === "file");
        const readme = files.find((f) =>
          f.name.toLowerCase().startsWith("readme"),
        );
        const autoSelect = readme ?? files[0] ?? null;
        if (autoSelect) {
          setSelectedPath(autoSelect.path);
        }
      })
      .catch((err) => {
        setTreeError(err instanceof Error ? err.message : "Failed to load files");
      })
      .finally(() => setTreeLoading(false));
  }, [baseUrl, taskId]);

  useEffect(() => {
    if (!selectedPath || !baseUrl) return;

    setFileLoading(true);
    setFileError(null);
    fetchFileContent(baseUrl, taskId, selectedPath)
      .then((data) => {
        setFileContent(data.content);
        setIsBinary(data.is_binary);
      })
      .catch((err) => {
        setFileError(err instanceof Error ? err.message : "Failed to load file");
      })
      .finally(() => setFileLoading(false));
  }, [selectedPath, baseUrl]);

  function handleDownload() {
    if (!baseUrl) return;
    window.location.href = `${baseUrl}/download`;
  }

  return (
    <div className="rounded-lg border">
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <h2 className="font-semibold text-sm">Source Code</h2>
        <Button
          variant="outline"
          size="sm"
          onClick={handleDownload}
          disabled={!baseUrl}
        >
          Download Code
        </Button>
      </div>

      {treeError && !treeLoading && (
        <div className="p-4">
          <p className="text-sm text-red-600">{treeError}</p>
        </div>
      )}

      {!treeError && (
        <div className="flex" style={{ minHeight: "320px", maxHeight: "560px" }}>
          <div className="w-60 border-r overflow-y-auto flex-shrink-0">
            {treeLoading ? (
              <div className="p-4 space-y-2">
                <div className="h-3 bg-muted animate-pulse rounded w-3/4" />
                <div className="h-3 bg-muted animate-pulse rounded w-1/2" />
              </div>
            ) : (
              <FileTree
                entries={entries}
                selectedPath={selectedPath}
                onSelect={setSelectedPath}
              />
            )}
          </div>
          <FileViewer
            content={fileContent}
            filePath={selectedPath}
            isBinary={isBinary}
            isLoading={fileLoading}
            error={fileError}
          />
        </div>
      )}
    </div>
  );
}
