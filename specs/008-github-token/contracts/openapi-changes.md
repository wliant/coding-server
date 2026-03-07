# OpenAPI Contract Changes: GitHub Token Integration (008)

Source of truth: `openapi.json` (repo root). Make these changes before any implementation.

---

## 1. `CreateTaskRequest` schema — add `branch` field

**Location in openapi.json**: `components.schemas.CreateTaskRequest.properties`

Add:
```json
"branch": {
  "anyOf": [
    { "type": "string", "maxLength": 255 },
    { "type": "null" }
  ],
  "title": "Branch",
  "description": "Git branch to clone and check out before the agent starts. If the branch does not exist on the remote, it will be created from the default branch. If null, the repository default branch is used.",
  "default": null
}
```

---

## 2. `TaskDetailResponse` schema — add `branch` field

**Location in openapi.json**: `components.schemas.TaskDetailResponse.properties`

Add:
```json
"branch": {
  "anyOf": [
    { "type": "string" },
    { "type": "null" }
  ],
  "title": "Branch",
  "description": "The git branch associated with this task, or null if none was specified.",
  "default": null
}
```

---

## 3. Settings — `github.token` key

No schema change to `UpdateSettingsRequest` or `SettingsResponse` (both use open `dict[str, str]`).

Update the description of `PUT /settings` in openapi.json to note that `github.token` is now a recognized key:

```json
"description": "Update one or more settings. Recognized keys include: agent.work.path, agent.simple_crewai.*, github.token."
```

---

## 4. Version bump

Increment `info.version` in openapi.json for the breaking change (new required-ish field on CreateTaskRequest):

```json
"info": {
  "version": "0.9.0"
}
```

(Current version is `0.8.0` — minor bump for additive changes.)

---

## Regenerate TypeScript client

After updating `openapi.json`, run:

```bash
cd web && npm run generate
```

This regenerates `web/src/client/` from the updated spec. Do this before writing any frontend code.
