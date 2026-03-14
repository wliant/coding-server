/**
 * Client for the API file proxy endpoints (/tasks/{id}/files).
 * Routes requests through the API server which proxies to the appropriate
 * source (worker, sandbox, or temp git clone).
 */

export interface FileEntry {
  name: string;
  path: string;
  type: "file" | "directory";
  size?: number | null;
  is_binary?: boolean | null;
}

export interface FileListResponse {
  root: string;
  entries: FileEntry[];
}

export interface FileContentResponse {
  path: string;
  content: string;
  size: number;
  is_binary: boolean;
}

const API_URL =
  typeof process !== "undefined"
    ? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
    : "http://localhost:8000";

export async function fetchTaskFiles(
  taskId: string,
): Promise<FileListResponse> {
  const resp = await fetch(
    `${API_URL}/tasks/${encodeURIComponent(taskId)}/files`,
  );
  if (!resp.ok) {
    const t = await resp.text();
    throw new Error(t || `HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function fetchTaskFileContent(
  taskId: string,
  filePath: string,
): Promise<FileContentResponse> {
  const encoded = filePath
    .split("/")
    .map(encodeURIComponent)
    .join("/");
  const resp = await fetch(
    `${API_URL}/tasks/${encodeURIComponent(taskId)}/files/${encoded}`,
  );
  if (!resp.ok) {
    const t = await resp.text();
    throw new Error(t || `HTTP ${resp.status}`);
  }
  return resp.json();
}
