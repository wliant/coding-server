"use client";

import React from "react";
import { useTheme } from "next-themes";
import SyntaxHighlighter from "react-syntax-highlighter";
import { githubGist } from "react-syntax-highlighter/dist/esm/styles/hljs";
import { atomOneDark } from "react-syntax-highlighter/dist/esm/styles/hljs";

interface FileViewerProps {
  content: string;
  filePath: string | null;
  isBinary: boolean;
  isLoading: boolean;
  error: string | null;
}

const EXT_TO_LANG: Record<string, string> = {
  py: "python",
  ts: "typescript",
  tsx: "typescript",
  js: "javascript",
  jsx: "javascript",
  json: "json",
  yaml: "yaml",
  yml: "yaml",
  md: "markdown",
  sh: "bash",
  bash: "bash",
  css: "css",
  html: "html",
  xml: "xml",
  sql: "sql",
  go: "go",
  rs: "rust",
  java: "java",
  rb: "ruby",
  toml: "toml",
};

function inferLanguage(filePath: string | null): string {
  if (!filePath) return "plaintext";
  const ext = filePath.split(".").pop()?.toLowerCase() ?? "";
  return EXT_TO_LANG[ext] ?? "plaintext";
}

export function FileViewer({
  content,
  filePath,
  isBinary,
  isLoading,
  error,
}: FileViewerProps) {
  const { resolvedTheme } = useTheme();
  if (isLoading) {
    return (
      <div className="flex-1 p-4 space-y-2">
        <div className="h-4 bg-muted animate-pulse rounded w-3/4" />
        <div className="h-4 bg-muted animate-pulse rounded w-full" />
        <div className="h-4 bg-muted animate-pulse rounded w-1/2" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 p-4">
        <p className="text-sm text-red-600">{error}</p>
      </div>
    );
  }

  if (!filePath) {
    return (
      <div className="flex-1 p-4 flex items-center justify-center">
        <p className="text-sm text-muted-foreground">Select a file to view</p>
      </div>
    );
  }

  if (isBinary) {
    return (
      <div className="flex-1 p-4 flex items-center justify-center">
        <p className="text-sm text-muted-foreground italic">
          Binary file — use Download to access it.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto text-xs">
      <SyntaxHighlighter
        language={inferLanguage(filePath)}
        style={resolvedTheme === "dark" ? atomOneDark : githubGist}
        showLineNumbers
        wrapLongLines={false}
        customStyle={{ margin: 0, borderRadius: 0, fontSize: "0.75rem" }}
      >
        {content}
      </SyntaxHighlighter>
    </div>
  );
}
