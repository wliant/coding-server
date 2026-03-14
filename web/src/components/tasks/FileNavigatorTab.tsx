"use client";

import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { FileTree } from "@/components/tasks/FileTree";
import { FileViewer } from "@/components/tasks/FileViewer";
import {
  fetchTaskFiles,
  fetchTaskFileContent,
  type FileEntry,
} from "@/lib/fileProxyClient";

interface FileNavigatorTabProps {
  taskId: string;
  workerUrl?: string | null;
  banner?: React.ReactNode;
}

export function FileNavigatorTab({
  taskId,
  workerUrl,
  banner,
}: FileNavigatorTabProps) {
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>("");
  const [isBinary, setIsBinary] = useState(false);
  const [treeLoading, setTreeLoading] = useState(true);
  const [treeError, setTreeError] = useState<string | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    setTreeLoading(true);
    fetchTaskFiles(taskId)
      .then((data) => {
        setEntries(data.entries);
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
  }, [taskId]);

  useEffect(() => {
    if (!selectedPath) return;

    setFileLoading(true);
    setFileError(null);
    fetchTaskFileContent(taskId, selectedPath)
      .then((data) => {
        setFileContent(data.content);
        setIsBinary(data.is_binary);
      })
      .catch((err) => {
        setFileError(err instanceof Error ? err.message : "Failed to load file");
      })
      .finally(() => setFileLoading(false));
  }, [selectedPath, taskId]);

  function handleDownload() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    window.location.href = `${apiUrl}/tasks/${taskId}/download`;
  }

  return (
    <div className="rounded-lg border">
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <h2 className="font-semibold text-sm">Files</h2>
        {workerUrl && (
          <Button variant="outline" size="sm" onClick={handleDownload}>
            Download Code
          </Button>
        )}
      </div>

      {banner && <div className="px-4 py-2 border-b">{banner}</div>}

      {treeError && !treeLoading && (
        <div className="p-4">
          <p className="text-sm text-red-600">{treeError}</p>
        </div>
      )}

      {!treeError && (
        <div className="flex" style={{ minHeight: "320px", maxHeight: "560px" }}>
          <div className="w-60 border-r overflow-y-auto flex-shrink-0">
            <div className="px-2 py-2 border-b">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Filter files..."
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  className="w-full px-2 py-1 text-xs border rounded bg-background placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                />
                {filter && (
                  <button
                    className="absolute right-1.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground text-xs"
                    onClick={() => setFilter("")}
                    aria-label="Clear filter"
                  >
                    ×
                  </button>
                )}
              </div>
            </div>
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
                filter={filter}
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
