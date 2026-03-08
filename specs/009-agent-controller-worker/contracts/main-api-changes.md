# Main API Contract Changes (openapi.json)

**Branch**: `009-agent-controller-worker` | **Date**: 2026-03-08

These changes must be applied to the root `openapi.json` before any implementation begins (Constitution Principle VI).

---

## Version Bump

`info.version`: `"0.5.0"` → `"0.6.0"` (minor bump; new endpoints + status values added)

---

## Modified: `TaskStatus` Enum

Add two new values:

```json
{
  "TaskStatus": {
    "type": "string",
    "enum": ["pending", "in_progress", "completed", "failed", "aborted", "cleaning_up", "cleaned"],
    "title": "TaskStatus"
  }
}
```

---

## Modified: `TaskDetailResponse`

Add new optional field:

```json
"assigned_worker_id": {
  "anyOf": [{"type": "string"}, {"type": "null"}],
  "title": "Assigned Worker Id",
  "description": "ID of the worker currently executing or that last executed this task.",
  "default": null
}
```

---

## New Endpoint: `POST /tasks/{task_id}/cleanup`

```json
"/tasks/{task_id}/cleanup": {
  "post": {
    "tags": ["tasks"],
    "summary": "Initiate Cleanup",
    "description": "Initiates cleanup for a completed or failed task. Transitions the task to 'cleaning_up' status. The Controller will asynchronously call the worker's /free endpoint. Only valid when task status is 'completed' or 'failed'.",
    "operationId": "initiateCleanupTasksTaskIdCleanupPost",
    "parameters": [
      {
        "name": "task_id",
        "in": "path",
        "required": true,
        "schema": {"type": "string", "format": "uuid", "title": "Task Id"}
      }
    ],
    "responses": {
      "200": {
        "description": "Cleanup initiated",
        "content": {
          "application/json": {
            "schema": {"$ref": "#/components/schemas/CleanupResponse"}
          }
        }
      },
      "404": {"description": "Task not found"},
      "409": {
        "description": "Task is not in a cleanable state (must be 'completed' or 'failed')"
      }
    }
  }
}
```

---

## New Schema: `CleanupResponse`

```json
"CleanupResponse": {
  "properties": {
    "task_id": {
      "type": "string",
      "format": "uuid",
      "title": "Task Id"
    },
    "status": {
      "type": "string",
      "enum": ["cleaning_up"],
      "title": "Status"
    }
  },
  "required": ["task_id", "status"],
  "title": "CleanupResponse",
  "type": "object"
}
```

---

## New Endpoint: `GET /workers`

Proxies to Controller's `GET /workers`. Allows the web frontend to display worker status via the existing API client.

```json
"/workers": {
  "get": {
    "tags": ["workers"],
    "summary": "List Workers",
    "description": "Returns all workers registered with the Controller, including their status, agent type, and last heartbeat time.",
    "operationId": "listWorkersWorkersGet",
    "responses": {
      "200": {
        "description": "List of registered workers",
        "content": {
          "application/json": {
            "schema": {
              "type": "array",
              "items": {"$ref": "#/components/schemas/WorkerStatus"},
              "title": "Workers"
            }
          }
        }
      },
      "503": {
        "description": "Controller is unreachable"
      }
    }
  }
}
```

---

## New Schema: `WorkerStatus`

```json
"WorkerStatus": {
  "properties": {
    "worker_id": {"type": "string", "title": "Worker Id"},
    "agent_type": {"type": "string", "title": "Agent Type"},
    "worker_url": {"type": "string", "title": "Worker Url"},
    "status": {
      "type": "string",
      "enum": ["free", "in_progress", "completed", "failed", "unreachable"],
      "title": "Status"
    },
    "current_task_id": {
      "anyOf": [{"type": "string"}, {"type": "null"}],
      "title": "Current Task Id",
      "default": null
    },
    "registered_at": {"type": "string", "format": "date-time", "title": "Registered At"},
    "last_heartbeat_at": {"type": "string", "format": "date-time", "title": "Last Heartbeat At"}
  },
  "required": ["worker_id", "agent_type", "worker_url", "status", "registered_at", "last_heartbeat_at"],
  "title": "WorkerStatus",
  "type": "object"
}
```

---

## Modified: `POST /tasks/{task_id}/push`

No change to the endpoint signature. Internal implementation changes (now proxies to worker), but the contract is unchanged.

---

## Removed: `agent.work.path` from Settings

The `agent.work.path` key is removed from the allowed settings. Document in `PUT /settings` description that this key is no longer supported.
