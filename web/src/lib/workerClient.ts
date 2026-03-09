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

export function getWorkerBaseUrl(
  assignedWorkerUrl: string | null | undefined,
): string {
  return (
    (typeof process !== "undefined"
      ? process.env.NEXT_PUBLIC_WORKER_URL
      : undefined) ??
    assignedWorkerUrl ??
    ""
  );
}

export async function fetchFileTree(
  baseUrl: string,
  taskId: string,
): Promise<FileListResponse> {
  const resp = await fetch(`${baseUrl}/files?task_id=${encodeURIComponent(taskId)}`);
  if (!resp.ok) {
    const t = await resp.text();
    throw new Error(t || `HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function fetchFileContent(
  baseUrl: string,
  taskId: string,
  filePath: string,
): Promise<FileContentResponse> {
  const encoded = filePath
    .split("/")
    .map(encodeURIComponent)
    .join("/");
  const resp = await fetch(`${baseUrl}/files/${encoded}?task_id=${encodeURIComponent(taskId)}`);
  if (!resp.ok) {
    const t = await resp.text();
    throw new Error(t || `HTTP ${resp.status}`);
  }
  return resp.json();
}
