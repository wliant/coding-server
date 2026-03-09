"use client";

import React from "react";
import type { DiffFileEntry, FileDiffResponse } from "@/lib/workerClient";

interface DiffViewerProps {
  diffFiles: DiffFileEntry[];
  selectedPath: string | null;
  onSelectFile: (path: string) => void;
  fileDiff: FileDiffResponse | null;
  isLoading: boolean;
  error: string | null;
}

const BADGE_STYLES: Record<string, string> = {
  modified: "bg-yellow-100 text-yellow-800",
  added: "bg-green-100 text-green-800",
  deleted: "bg-red-100 text-red-800",
  renamed: "bg-blue-100 text-blue-800",
};

const BADGE_LABELS: Record<string, string> = {
  modified: "M",
  added: "A",
  deleted: "D",
  renamed: "R",
};

interface ParsedLine {
  type: "file-header" | "hunk-header" | "addition" | "deletion" | "context";
  content: string;
  oldLineNo: number | null;
  newLineNo: number | null;
}

function parseDiff(diffText: string): ParsedLine[] {
  const lines = diffText.split("\n");
  const result: ParsedLine[] = [];
  let oldLine = 0;
  let newLine = 0;

  for (const raw of lines) {
    if (raw.startsWith("---") || raw.startsWith("+++")) {
      result.push({ type: "file-header", content: raw, oldLineNo: null, newLineNo: null });
    } else if (raw.startsWith("@@")) {
      // Parse @@ -<old_start>,<old_count> +<new_start>,<new_count> @@
      const m = raw.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
      if (m) {
        oldLine = parseInt(m[1], 10);
        newLine = parseInt(m[2], 10);
      }
      result.push({ type: "hunk-header", content: raw, oldLineNo: null, newLineNo: null });
    } else if (raw.startsWith("+")) {
      result.push({ type: "addition", content: raw.slice(1), oldLineNo: null, newLineNo: newLine });
      newLine++;
    } else if (raw.startsWith("-")) {
      result.push({ type: "deletion", content: raw.slice(1), oldLineNo: oldLine, newLineNo: null });
      oldLine++;
    } else if (raw.startsWith(" ") || raw === "") {
      result.push({ type: "context", content: raw.startsWith(" ") ? raw.slice(1) : raw, oldLineNo: oldLine, newLineNo: newLine });
      oldLine++;
      newLine++;
    }
  }

  return result;
}

function DiffLine({ line }: { line: ParsedLine }) {
  if (line.type === "file-header") {
    return (
      <tr className="bg-muted/30">
        <td className="px-2 py-0 text-right text-xs text-muted-foreground w-10 select-none border-r" />
        <td className="px-2 py-0 text-right text-xs text-muted-foreground w-10 select-none border-r" />
        <td className="px-2 py-0 text-xs text-muted-foreground font-mono whitespace-pre">{line.content}</td>
      </tr>
    );
  }

  if (line.type === "hunk-header") {
    return (
      <tr className="bg-[#ddf4ff]">
        <td className="px-2 py-0 text-right text-xs text-[#0550ae] w-10 select-none border-r" />
        <td className="px-2 py-0 text-right text-xs text-[#0550ae] w-10 select-none border-r" />
        <td className="px-2 py-0 text-xs text-[#0550ae] font-mono whitespace-pre">{line.content}</td>
      </tr>
    );
  }

  if (line.type === "addition") {
    return (
      <tr className="bg-[#e6ffec]">
        <td className="px-2 py-0 text-right text-xs text-[#1a7f37] w-10 select-none border-r" />
        <td className="px-2 py-0 text-right text-xs text-[#1a7f37] w-10 select-none border-r">
          {line.newLineNo}
        </td>
        <td className="px-2 py-0 text-xs font-mono whitespace-pre text-[#1a7f37]">
          <span className="select-none mr-1">+</span>{line.content}
        </td>
      </tr>
    );
  }

  if (line.type === "deletion") {
    return (
      <tr className="bg-[#ffebe9]">
        <td className="px-2 py-0 text-right text-xs text-[#cf222e] w-10 select-none border-r">
          {line.oldLineNo}
        </td>
        <td className="px-2 py-0 text-right text-xs text-[#cf222e] w-10 select-none border-r" />
        <td className="px-2 py-0 text-xs font-mono whitespace-pre text-[#cf222e]">
          <span className="select-none mr-1">-</span>{line.content}
        </td>
      </tr>
    );
  }

  // context
  return (
    <tr className="bg-white">
      <td className="px-2 py-0 text-right text-xs text-muted-foreground w-10 select-none border-r">
        {line.oldLineNo}
      </td>
      <td className="px-2 py-0 text-right text-xs text-muted-foreground w-10 select-none border-r">
        {line.newLineNo}
      </td>
      <td className="px-2 py-0 text-xs font-mono whitespace-pre text-foreground">
        <span className="select-none mr-1"> </span>{line.content}
      </td>
    </tr>
  );
}

export function DiffViewer({
  diffFiles,
  selectedPath,
  onSelectFile,
  fileDiff,
  isLoading,
  error,
}: DiffViewerProps) {
  const parsedLines = fileDiff?.diff ? parseDiff(fileDiff.diff) : [];

  return (
    <div className="flex" style={{ minHeight: "320px", maxHeight: "560px" }}>
      {/* Left panel — changed file list */}
      <div className="w-60 border-r overflow-y-auto flex-shrink-0">
        {isLoading ? (
          <div className="p-4 space-y-2">
            <div className="h-3 bg-muted animate-pulse rounded w-3/4" />
            <div className="h-3 bg-muted animate-pulse rounded w-1/2" />
          </div>
        ) : diffFiles.length === 0 ? (
          <div className="p-4 text-xs text-muted-foreground">No changes detected</div>
        ) : (
          <ul className="py-1">
            {diffFiles.map((f) => (
              <li key={f.path}>
                <button
                  className={`w-full flex items-start gap-1.5 px-3 py-1.5 text-left hover:bg-muted/50 transition-colors ${
                    selectedPath === f.path ? "bg-muted" : ""
                  }`}
                  onClick={() => onSelectFile(f.path)}
                >
                  <span
                    className={`mt-0.5 flex-shrink-0 text-[10px] font-bold w-4 h-4 flex items-center justify-center rounded ${
                      BADGE_STYLES[f.change_type] ?? "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {BADGE_LABELS[f.change_type] ?? "?"}
                  </span>
                  <span className="flex-1 min-w-0">
                    <span className="block text-xs truncate">{f.path}</span>
                    <span className="text-[10px] text-muted-foreground">
                      {f.additions > 0 && (
                        <span className="text-[#1a7f37]">+{f.additions} </span>
                      )}
                      {f.deletions > 0 && (
                        <span className="text-[#cf222e]">-{f.deletions}</span>
                      )}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Right panel — unified diff renderer */}
      <div className="flex-1 overflow-auto">
        {!selectedPath ? (
          <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
            Select a file to view diff
          </div>
        ) : error ? (
          <div className="p-4 text-sm text-red-600">{error}</div>
        ) : !fileDiff ? (
          <div className="p-4 space-y-1">
            <div className="h-3 bg-muted animate-pulse rounded w-full" />
            <div className="h-3 bg-muted animate-pulse rounded w-4/5" />
          </div>
        ) : fileDiff.diff === "" ? (
          <div className="p-4 text-sm text-muted-foreground">Binary file — no text diff available</div>
        ) : (
          <table className="w-full border-collapse text-xs leading-5">
            <tbody>
              {parsedLines.map((line, i) => (
                <DiffLine key={i} line={line} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
