import { test, expect } from "@playwright/test";

const API_URL = process.env.API_URL || "http://localhost:8000";
const WORKER_URL = process.env.WORKER_URL || "http://localhost:8001";
const TOOLS_URL = process.env.TOOLS_URL || "http://localhost:8002";
const BASE_URL = process.env.BASE_URL || "http://localhost:3000";

test("api health endpoint returns ok", async ({ request }) => {
  const response = await request.get(`${API_URL}/health`);
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.status).toBe("ok");
});

test("worker health endpoint returns ok", async ({ request }) => {
  const response = await request.get(`${WORKER_URL}/health`);
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.status).toBe("ok");
});

test("tools health endpoint returns ok", async ({ request }) => {
  const response = await request.get(`${TOOLS_URL}/health`);
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.status).toBe("ok");
});

test("web health endpoint returns ok", async ({ request }) => {
  const response = await request.get(`${BASE_URL}/api/health`);
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.status).toBe("ok");
});
