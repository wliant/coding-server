# Feature Specification: Agent Settings Configuration

**Feature Branch**: `007-agent-settings`
**Created**: 2026-03-07
**Status**: Draft
**Input**: User description: "Agent Setting - Many different agents can be selected to work on a task. Currently we have 3 selections in the dropdown, and only 1 is actually implemented - simple_crewai_pair_agent. For each agent, we need to be able to configure it in the settings page. In Settings page, add 1 section for agent setting, currently only allow configuring simple_crewai_pair_agent. Look at the agent source code and see what are the configurations needed and allow it to be configured. This includes Ollama base url, and everything. In previous specification, it was determined that all configurations should use environment variables, it is no longer true. It is strictly coming from configuration only. So when using the library, allow these configurations to be passed by the caller."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure Agent LLM Settings in UI (Priority: P1)

An operator visits the Settings page and navigates to a new "Agent Settings" tab. Under a "simple_crewai_pair_agent" section, they see fields for LLM provider, model name, temperature, Ollama base URL, and API keys for OpenAI and Anthropic. They update the values, save, and the next task execution uses those new settings.

**Why this priority**: This is the core of the feature — without it, there is no way to configure agents through the UI. All other stories depend on these settings being persisted.

**Independent Test**: Open Settings → Agent Settings tab, update the Ollama base URL, save, then submit a task and verify it runs against the new URL.

**Acceptance Scenarios**:

1. **Given** the Settings page is open, **When** the user clicks the "Agent Settings" tab, **Then** a section titled "simple_crewai_pair_agent" is shown with fields: LLM Provider, Model, Temperature, Ollama Base URL, OpenAI API Key, Anthropic API Key.
2. **Given** all fields are populated, **When** the user clicks Save, **Then** the values are persisted and the page reflects the saved values after reload.
3. **Given** a task is submitted, **When** the worker executes it, **Then** the agent uses the LLM settings from the saved configuration (not from environment variables).
4. **Given** no agent settings have been saved yet, **When** the user opens Agent Settings, **Then** default values are shown (provider: "ollama", model: "qwen2.5-coder:7b", temperature: 0.2, Ollama URL: "http://localhost:11434", API keys empty).

---

### User Story 2 - Switch LLM Provider (Priority: P2)

An operator wants to switch from Ollama to OpenAI. They go to Agent Settings, change the provider to "openai", enter their API key, update the model name, and save. Subsequent task runs use the OpenAI endpoint.

**Why this priority**: The primary value of configurable LLM settings is the ability to switch providers without redeploying. This validates the end-to-end flow for non-default providers.

**Independent Test**: Set provider to "openai" with a valid API key, run a task, and confirm the job does not attempt to connect to Ollama.

**Acceptance Scenarios**:

1. **Given** provider is set to "openai", **When** the worker runs an agent, **Then** the agent is configured with the OpenAI API key and model (not Ollama URL).
2. **Given** provider is set to "anthropic", **When** the worker runs an agent, **Then** the agent is configured with the Anthropic API key and model.
3. **Given** provider is set to "ollama", **When** the worker runs an agent, **Then** the agent uses the configured Ollama base URL.

---

### User Story 3 - Validate Temperature Input (Priority: P3)

A user enters an invalid value for temperature (e.g., "abc" or "3.0"), clicks Save, and receives a clear validation error explaining the valid range (0.0–2.0) without saving invalid data.

**Why this priority**: Protects data integrity. Can be verified in isolation on the form without running an actual agent.

**Independent Test**: Enter "-1" in the temperature field and click Save; verify an error message appears and no save occurs.

**Acceptance Scenarios**:

1. **Given** temperature is set to a non-numeric value, **When** the user saves, **Then** an error message is shown and the value is not persisted.
2. **Given** temperature is outside the range 0.0–2.0, **When** the user saves, **Then** an error message is shown indicating the valid range.
3. **Given** temperature is a valid number within range, **When** the user saves, **Then** the value is persisted successfully.

---

### Edge Cases

- What happens when the worker starts before any agent settings have been saved? The worker fetches settings from the API; missing keys use built-in defaults so tasks still execute without manual configuration.
- What happens if the settings API is unreachable when the worker tries to fetch settings? The job is failed immediately with a clear "unable to fetch settings" error message.
- What happens if the API key field is left blank for a non-Ollama provider? The agent run fails; the job is marked failed with a meaningful error message.
- What happens if the Ollama base URL is unreachable at task execution time? The agent run fails and the job is marked failed; no silent retries at the settings level.
- What happens if a user saves a partial update (e.g., only changes the model)? Only the changed fields are updated; other settings retain their currently persisted values.
- What happens if the user sets an unrecognised LLM provider value? The API rejects it with a validation error and the value is not persisted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Settings page MUST expose an "Agent Settings" tab alongside the existing "General" tab.
- **FR-002**: The "Agent Settings" tab MUST contain a "simple_crewai_pair_agent" section with the following configurable fields: LLM Provider (selection from: ollama, openai, anthropic), Model Name (free text), Temperature (numeric, 0.0–2.0), Ollama Base URL (text), OpenAI API Key (masked text), Anthropic API Key (masked text).
- **FR-003**: The system MUST persist all agent settings fields in the existing key/value settings store under namespaced keys: `agent.simple_crewai.llm_provider`, `agent.simple_crewai.llm_model`, `agent.simple_crewai.llm_temperature`, `agent.simple_crewai.ollama_base_url`, `agent.simple_crewai.openai_api_key`, `agent.simple_crewai.anthropic_api_key`.
- **FR-004**: The settings API MUST accept and validate all new agent settings keys; submitting an unknown key MUST be rejected with a clear error.
- **FR-005**: Temperature MUST be validated as a decimal number in the range 0.0–2.0; saving an out-of-range or non-numeric value MUST be rejected with an error message shown to the user.
- **FR-006**: The system MUST provide default values for all agent settings fields so a fresh deployment executes tasks without manual configuration (defaults: provider=ollama, model=qwen2.5-coder:7b, temperature=0.2, ollama_base_url=http://localhost:11434, openai_api_key="", anthropic_api_key="").
- **FR-007**: The worker MUST fetch LLM configuration by calling the API's `GET /settings` endpoint at job-execution time, not from environment variables.
- **FR-008**: The worker MUST use built-in defaults for any agent settings key that is absent from the store; LLM environment variables are removed and no longer serve as a fallback.
- **FR-009**: The agent library (simple_crewai_pair_agent) MUST accept all LLM configuration values exclusively from the caller-provided config object; it MUST NOT read LLM settings from environment variables.
- **FR-010**: API key input fields in the UI MUST always display a fixed masked placeholder (e.g., `••••••••`) regardless of whether a value is stored; the user clears the field and retypes to change a saved key.
- **FR-011**: LLM Provider MUST be validated against the supported set (ollama, openai, anthropic); unsupported values MUST be rejected.
- **FR-012**: If the worker cannot reach the settings API at job-execution time, the job MUST be marked failed immediately with an error message of "unable to fetch agent settings"; the worker MUST NOT proceed with built-in defaults in this scenario.

### Key Entities

- **AgentSetting**: A persisted configuration value for an agent. Attributes: key (namespaced string), value (plain text string — no encryption), updated_at (timestamp). Stored in the existing `settings` table — no new table required.
- **CodingAgentConfig**: The immutable configuration object passed to the simple_crewai_pair_agent library at runtime. Contains all LLM fields (provider, model, temperature, urls, keys) plus per-run inputs (working directory, project name, requirement). All LLM fields must be supplied by the caller.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can update any of the 6 agent LLM configuration fields and have that change take effect on the next task run, without restarting any service or modifying environment variables.
- **SC-002**: All 6 configuration fields are visible and editable from the Settings page Agent Settings tab on both desktop and tablet screen sizes.
- **SC-003**: Invalid temperature values (out-of-range or non-numeric) are rejected with an explanatory message before submission; no invalid data reaches the backend.
- **SC-004**: A task submitted after changing the LLM provider correctly routes to the newly configured provider, as evidenced by the job's execution log or error output.
- **SC-005**: A fresh deployment with no saved agent settings executes tasks successfully using built-in defaults (Ollama + qwen2.5-coder:7b at http://localhost:11434).

## Clarifications

### Session 2026-03-07

- Q: Should API keys (OpenAI, Anthropic) be stored with any additional protection? → A: Plain text in DB — no additional encryption, consistent with all other settings in the key/value store.
- Q: How should the worker fetch LLM settings at job-execution time? → A: Worker calls the API's `GET /settings` HTTP endpoint before each job run.
- Q: What should API key fields display when a value has already been saved? → A: Show a fixed masked placeholder (e.g., `••••••••`); user must clear and retype to change the value.
- Q: After this feature, what should happen to the LLM-related environment variables in the worker config? → A: Remove entirely — settings store is the sole source of truth; no env var fallback.
- Q: What should the worker do if the settings API is unreachable at job-execution time? → A: Fail the job immediately with a clear "unable to fetch settings" error message.

## Assumptions

- The existing `settings` table (key/value store) is sufficient to hold all new agent settings; no new table or Alembic migration for new columns is required.
- The worker has network access to the API at job-execution time and fetches settings via `GET /settings` before constructing the agent config.
- The three LLM providers supported are exactly: `ollama`, `openai`, `anthropic`, matching the current agent library implementation.
- The two other agent options shown in the task-submission dropdown are not yet implemented; no settings UI for them is in scope for this feature.
- Saving agent settings is a full-panel save (all 6 fields submitted together), not individual field saves.
- The LLM-related environment variables (`LLM_PROVIDER`, `LLM_MODEL`, `LLM_TEMPERATURE`, `OLLAMA_BASE_URL`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) are removed from the worker config as part of this feature.
- The `OPENAI_API_KEY` environment variable workaround in the agent library's initialiser (satisfying a CrewAI import-time check) must be removed; it should be satisfied from the config object rather than from the environment.
