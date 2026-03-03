/**
 * @jest-environment node
 */
import { GET } from "../../src/app/api/health/route";

test("returns ok status", async () => {
  const res = await GET();
  const body = await res.json();
  expect(body.status).toBe("ok");
});
