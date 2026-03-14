export function getWorkerBaseUrl(
  assignedWorkerUrl: string | null | undefined,
): string {
  if (assignedWorkerUrl) {
    // The assigned URL uses internal container hostnames (e.g. http://host:8005).
    // Replace the hostname with localhost so the browser can reach it.
    try {
      const parsed = new URL(assignedWorkerUrl);
      parsed.hostname = "localhost";
      return parsed.origin;
    } catch {
      // Fall through to env var fallback
    }
  }
  return (
    (typeof process !== "undefined"
      ? process.env.NEXT_PUBLIC_WORKER_URL
      : undefined) ?? ""
  );
}

export interface DiffFileEntry {
  path: string;
  change_type: "modified" | "added" | "deleted" | "renamed";
  additions: number;
  deletions: number;
  old_path?: string | null;
}

export interface DiffListResponse {
  changed_files: DiffFileEntry[];
  total_additions: number;
  total_deletions: number;
}

export interface FileDiffResponse {
  path: string;
  diff: string;
  is_new_file: boolean;
}

export async function fetchDiffList(
  baseUrl: string,
  taskId: string,
): Promise<DiffListResponse> {
  const resp = await fetch(`${baseUrl}/diff?task_id=${encodeURIComponent(taskId)}`);
  if (!resp.ok) {
    const t = await resp.text();
    throw new Error(t || `HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function fetchFileDiff(
  baseUrl: string,
  taskId: string,
  filePath: string,
): Promise<FileDiffResponse> {
  const encoded = filePath
    .split("/")
    .map(encodeURIComponent)
    .join("/");
  const resp = await fetch(`${baseUrl}/diff/${encoded}?task_id=${encodeURIComponent(taskId)}`);
  if (!resp.ok) {
    const t = await resp.text();
    throw new Error(t || `HTTP ${resp.status}`);
  }
  return resp.json();
}
