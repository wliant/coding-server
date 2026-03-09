"use client";

import React, { useState } from "react";
import type { FileEntry } from "@/lib/workerClient";

interface TreeNode {
  name: string;
  path: string;
  type: "file" | "directory";
  children: TreeNode[];
  size?: number | null;
  is_binary?: boolean | null;
}

function buildTree(entries: FileEntry[]): TreeNode[] {
  const root: TreeNode[] = [];
  const nodeMap = new Map<string, TreeNode>();

  // Sort entries so directories come before files and alphabetically
  const sorted = [...entries].sort((a, b) => {
    if (a.type !== b.type) return a.type === "directory" ? -1 : 1;
    return a.path.localeCompare(b.path);
  });

  for (const entry of sorted) {
    const node: TreeNode = {
      name: entry.name,
      path: entry.path,
      type: entry.type,
      children: [],
      size: entry.size,
      is_binary: entry.is_binary,
    };
    nodeMap.set(entry.path, node);

    const parts = entry.path.split("/");
    if (parts.length === 1) {
      root.push(node);
    } else {
      const parentPath = parts.slice(0, -1).join("/");
      const parent = nodeMap.get(parentPath);
      if (parent) {
        parent.children.push(node);
      } else {
        // Parent not yet in map (shouldn't happen if API returns all dirs)
        root.push(node);
      }
    }
  }

  return root;
}

interface FileTreeProps {
  entries: FileEntry[];
  selectedPath: string | null;
  onSelect: (path: string) => void;
}

interface TreeNodeViewProps {
  node: TreeNode;
  depth: number;
  selectedPath: string | null;
  onSelect: (path: string) => void;
  expandedDirs: Set<string>;
  toggleDir: (path: string) => void;
}

function TreeNodeView({
  node,
  depth,
  selectedPath,
  onSelect,
  expandedDirs,
  toggleDir,
}: TreeNodeViewProps) {
  const paddingLeft = 8 + depth * 16;
  const isExpanded = expandedDirs.has(node.path);
  const isSelected = selectedPath === node.path;

  if (node.type === "directory") {
    return (
      <div>
        <button
          className="w-full text-left flex items-center gap-1 py-0.5 px-2 hover:bg-muted/60 text-sm"
          style={{ paddingLeft }}
          onClick={() => toggleDir(node.path)}
        >
          <span className="text-muted-foreground select-none">
            {isExpanded ? "▾" : "▸"}
          </span>
          <span className="font-medium truncate">{node.name}</span>
        </button>
        {isExpanded &&
          node.children.map((child) => (
            <TreeNodeView
              key={child.path}
              node={child}
              depth={depth + 1}
              selectedPath={selectedPath}
              onSelect={onSelect}
              expandedDirs={expandedDirs}
              toggleDir={toggleDir}
            />
          ))}
      </div>
    );
  }

  return (
    <button
      className={`w-full text-left flex items-center py-0.5 px-2 text-sm truncate hover:bg-muted/60 ${
        isSelected ? "bg-muted font-medium" : ""
      }`}
      style={{ paddingLeft }}
      onClick={() => onSelect(node.path)}
      title={node.path}
    >
      {node.name}
    </button>
  );
}

export function FileTree({ entries, selectedPath, onSelect }: FileTreeProps) {
  const tree = buildTree(entries);

  // Default: expand all top-level directories
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(() => {
    const topDirs = new Set<string>();
    for (const node of tree) {
      if (node.type === "directory") topDirs.add(node.path);
    }
    return topDirs;
  });

  function toggleDir(path: string) {
    setExpandedDirs((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }

  if (entries.length === 0) {
    return (
      <div className="p-4">
        <p className="text-sm text-muted-foreground">
          No files in working directory.
        </p>
      </div>
    );
  }

  return (
    <div className="py-1">
      {tree.map((node) => (
        <TreeNodeView
          key={node.path}
          node={node}
          depth={0}
          selectedPath={selectedPath}
          onSelect={onSelect}
          expandedDirs={expandedDirs}
          toggleDir={toggleDir}
        />
      ))}
    </div>
  );
}
