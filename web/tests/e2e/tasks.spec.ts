import { test, expect } from "@playwright/test";

const API_URL = process.env.API_URL || "http://localhost:8000";

test("POST /tasks creates a pending task and GET /tasks/{id} returns detail", async ({
  request,
}) => {
  // TODO: agent_id is now required by CreateTaskRequest.
  // These e2e tests need to first call GET /agents to look up an agent_id at runtime.
  const createResponse = await request.post(`${API_URL}/tasks`, {
    data: {
      project_type: "new",
      requirements: "E2E test: add a hello world function",
      git_url: "https://github.com/example/repo.git",
    },
  });
  expect(createResponse.status()).toBe(201);
  const created = await createResponse.json();
  expect(created.status).toBe("pending");
  expect(created.requirements).toBe("E2E test: add a hello world function");

  const taskId: string = created.id;

  // Fetch task detail
  const detailResponse = await request.get(`${API_URL}/tasks/${taskId}`);
  expect(detailResponse.status()).toBe(200);
  const detail = await detailResponse.json();

  expect(detail.id).toBe(taskId);
  expect(detail.status).toBe("pending");
  expect(detail.requirements).toBe("E2E test: add a hello world function");
  expect(detail.project).toHaveProperty("git_url");
  expect(detail.project.git_url).toBe("https://github.com/example/repo.git");
  expect(detail).toHaveProperty("started_at");
  expect(detail).toHaveProperty("completed_at");
  expect(detail).toHaveProperty("work_directory_path");
  expect(detail).toHaveProperty("elapsed_seconds");
  expect(detail.work_directory_path).toBeNull();
  expect(detail.elapsed_seconds).toBeNull();
});

test("GET /tasks/{id} returns 404 for unknown task", async ({ request }) => {
  const fakeId = "00000000-0000-0000-0000-000000000000";
  const response = await request.get(`${API_URL}/tasks/${fakeId}`);
  expect(response.status()).toBe(404);
});

test("POST /tasks/{id}/push returns 409 for non-completed task", async ({
  request,
}) => {
  // TODO: agent_id is now required — need to fetch from GET /agents first.
  const createResponse = await request.post(`${API_URL}/tasks`, {
    data: {
      project_type: "new",
      requirements: "E2E push test task",
    },
  });
  expect(createResponse.status()).toBe(201);
  const taskId: string = (await createResponse.json()).id;

  // Attempt push on pending task
  const pushResponse = await request.post(`${API_URL}/tasks/${taskId}/push`);
  expect(pushResponse.status()).toBe(409);
});

test("POST /tasks/{id}/push returns 404 for unknown task", async ({
  request,
}) => {
  const fakeId = "00000000-0000-0000-0000-000000000001";
  const response = await request.post(`${API_URL}/tasks/${fakeId}/push`);
  expect(response.status()).toBe(404);
});

test("GET /tasks returns list including newly created task", async ({
  request,
}) => {
  // TODO: agent_id is now required — need to fetch from GET /agents first.
  const createResponse = await request.post(`${API_URL}/tasks`, {
    data: {
      project_type: "new",
      requirements: "E2E list task check",
    },
  });
  expect(createResponse.status()).toBe(201);
  const taskId: string = (await createResponse.json()).id;

  // List tasks
  const listResponse = await request.get(`${API_URL}/tasks`);
  expect(listResponse.status()).toBe(200);
  const tasks = await listResponse.json();
  expect(Array.isArray(tasks)).toBeTruthy();
  const found = tasks.find((t: { id: string }) => t.id === taskId);
  expect(found).toBeDefined();
});
