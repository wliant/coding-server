import { test, expect } from "@playwright/test";

const API_URL = process.env.API_URL || "http://localhost:8000";

test("GET /projects returns array", async ({ request }) => {
  const response = await request.get(`${API_URL}/projects`);
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(Array.isArray(body)).toBeTruthy();
});

test("GET /health returns component statuses", async ({ request }) => {
  const response = await request.get(`${API_URL}/health`);
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body).toHaveProperty("components");
  expect(body.components).toHaveProperty("database");
  expect(body.components).toHaveProperty("redis");
});
