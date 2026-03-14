"use client";

import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FileTree } from "@/components/tasks/FileTree";
import { FileViewer } from "@/components/tasks/FileViewer";
import { DiffViewer } from "@/components/tasks/DiffViewer";
import {
  getWorkerBaseUrl,
  fetchFileTree,
  fetchFileContent,
  fetchDiffList,
  fetchFileDiff,
  type FileEntry,
  type DiffFileEntry,
  type FileDiffResponse,
} from "@/lib/workerClient";

interface SourceCodeSectionProps {
  taskId: string;
  workerUrl: string | null | undefined;
  isNewProject?: boolean;
}

export function SourceCodeSection({
  taskId,
  workerUrl,
  isNewProject = false,
}: SourceCodeSectionProps) {
  const baseUrl = getWorkerBaseUrl(workerUrl);

  // Source mode state
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>("");
  const [isBinary, setIsBinary] = useState(false);
  const [treeLoading, setTreeLoading] = useState(true);
  const [treeError, setTreeError] = useState<string | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);

  // Diff mode state
  const [viewMode, setViewMode] = useState<"source" | "diff">("source");
  const [diffFiles, setDiffFiles] = useState<DiffFileEntry[]>([]);
  const [diffLoading, setDiffLoading] = useState(false);
  const [diffError, setDiffError] = useState<string | null>(null);
  const [selectedDiffPath, setSelectedDiffPath] = useState<string | null>(null);
  const [fileDiff, setFileDiff] = useState<FileDiffResponse | null>(null);
  const [fileDiffLoading, setFileDiffLoading] = useState(false);
  const [fileDiffError, setFileDiffError] = useState<string | null>(null);

  // Load file tree (source mode)
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

  // Load file content (source mode)
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

  // Load diff list when switching to diff mode
  useEffect(() => {
    if (viewMode !== "diff" || !baseUrl) return;

    setDiffLoading(true);
    setDiffError(null);
    fetchDiffList(baseUrl, taskId)
      .then((data) => {
        setDiffFiles(data.changed_files);
        if (data.changed_files.length > 0 && !selectedDiffPath) {
          setSelectedDiffPath(data.changed_files[0].path);
        }
      })
      .catch((err) => {
        setDiffError(err instanceof Error ? err.message : "Failed to load diff");
      })
      .finally(() => setDiffLoading(false));
  }, [viewMode, baseUrl, taskId]);

  // Load file diff when a diff file is selected
  useEffect(() => {
    if (!selectedDiffPath || !baseUrl) return;

    setFileDiffLoading(true);
    setFileDiffError(null);
    setFileDiff(null);
    fetchFileDiff(baseUrl, taskId, selectedDiffPath)
      .then((data) => setFileDiff(data))
      .catch((err) => {
        setFileDiffError(err instanceof Error ? err.message : "Failed to load file diff");
      })
      .finally(() => setFileDiffLoading(false));
  }, [selectedDiffPath, baseUrl, taskId]);

  function handleDownload() {
    if (!baseUrl) return;
    window.location.href = `${baseUrl}/download`;
  }

  return (
    <div className="rounded-lg border">
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <div className="flex items-center gap-3">
          <h2 className="font-semibold text-sm">Source Code</h2>
          {!isNewProject && (
            <Tabs
              value={viewMode}
              onValueChange={(v) => setViewMode(v as "source" | "diff")}
            >
              <TabsList className="h-7">
                <TabsTrigger value="source" className="text-xs px-3 h-6">
                  Source
                </TabsTrigger>
                <TabsTrigger value="diff" className="text-xs px-3 h-6">
                  Diff
                </TabsTrigger>
              </TabsList>
            </Tabs>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleDownload}
          disabled={!baseUrl}
        >
          Download Code
        </Button>
      </div>

      {/* Source mode */}
      {viewMode === "source" && (
        <>
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
        </>
      )}

      {/* Diff mode */}
      {viewMode === "diff" && !isNewProject && (
        <>
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
        </>
      )}
    </div>
  );
}
