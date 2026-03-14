"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { AgentResponse, TaskType } from "@/client/types.gen";
import { TASK_TYPE_LABELS_LONG } from "@/lib/task-type-labels";

export interface TaskFormValues {
  task_type: TaskType;
  project_name?: string;
  agent_id: string;
  git_url?: string;
  branch?: string;
  requirements: string;
  commits_to_review?: number;
  required_capabilities?: string[];
}

interface TaskFormProps {
  agents: AgentResponse[];
  onSubmit: (data: TaskFormValues) => Promise<void>;
  initialValues?: Partial<TaskFormValues>;
  isSubmitting?: boolean;
}

const TASK_TYPE_OPTIONS: { value: TaskType; label: string }[] = (
  Object.entries(TASK_TYPE_LABELS_LONG) as [TaskType, string][]
).map(([value, label]) => ({ value, label }));

const REQUIREMENTS_CONFIG: Record<TaskType, { label: string; placeholder: string }> = {
  build_feature: { label: "Feature Description", placeholder: "Describe the feature to build..." },
  fix_bug: { label: "Bug Description", placeholder: "Describe the bug to fix..." },
  review_code: { label: "Review Instructions", placeholder: "What should the review focus on?" },
  refactor_code: { label: "Refactoring Goals", placeholder: "Describe what to refactor..." },
  write_tests: { label: "Testing Requirements", placeholder: "Describe what tests to write..." },
  scaffold_project: { label: "Project Description", placeholder: "Describe the project to scaffold..." },
};

const DEFAULT_VALUES: TaskFormValues = {
  task_type: "build_feature",
  project_name: "",
  agent_id: "",
  git_url: "",
  branch: "",
  requirements: "",
};

export function TaskForm({
  agents,
  onSubmit,
  initialValues,
  isSubmitting = false,
}: TaskFormProps) {
  const merged = { ...DEFAULT_VALUES, ...initialValues };

  const [taskType, setTaskType] = useState<TaskType>(merged.task_type);
  const [projectName, setProjectName] = useState<string>(merged.project_name ?? "");
  const [agentId, setAgentId] = useState<string>(merged.agent_id ?? "");
  const [gitUrl, setGitUrl] = useState<string>(merged.git_url ?? "");
  const [branch, setBranch] = useState<string>(merged.branch ?? "");
  const [requirements, setRequirements] = useState<string>(merged.requirements);
  const [commitsToReview, setCommitsToReview] = useState<string>(
    merged.commits_to_review != null ? String(merged.commits_to_review) : ""
  );
  const [capabilitiesInput, setCapabilitiesInput] = useState<string>(
    merged.required_capabilities?.join(", ") ?? ""
  );

  const isScaffold = taskType === "scaffold_project";
  const isReview = taskType === "review_code";

  const isProjectNameValid = isScaffold ? projectName.trim().length > 0 : true;
  const isGitUrlValid = isScaffold ? true : gitUrl.trim().length > 0;
  const isBranchValid = isReview ? branch.trim().length > 0 : true;
  const isAgentSelected = agentId.trim().length > 0;
  const isRequirementsValid = requirements.trim().length > 0;
  const isFormValid =
    isProjectNameValid && isGitUrlValid && isBranchValid && isAgentSelected && isRequirementsValid;

  const reqConfig = REQUIREMENTS_CONFIG[taskType];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isFormValid || isSubmitting) return;

    const data: TaskFormValues = {
      task_type: taskType,
      project_name: isScaffold ? projectName.trim() : undefined,
      agent_id: agentId,
      git_url: gitUrl.trim() || undefined,
      branch: branch.trim() || undefined,
      requirements,
    };

    if (isReview && commitsToReview.trim()) {
      data.commits_to_review = parseInt(commitsToReview, 10);
    }

    const caps = capabilitiesInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (caps.length > 0) {
      data.required_capabilities = caps;
    }

    await onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 max-w-2xl">
      {/* Task Type */}
      <div className="space-y-2">
        <label
          htmlFor="task-type-select"
          className="block text-sm font-medium text-foreground"
        >
          Task Type <span className="text-red-500">*</span>
        </label>
        <Select
          value={taskType}
          onValueChange={(v) => {
            setTaskType(v as TaskType);
          }}
        >
          <SelectTrigger id="task-type-select" aria-label="Task type">
            <SelectValue placeholder="Select a task type" />
          </SelectTrigger>
          <SelectContent>
            {TASK_TYPE_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Project Name — only for scaffold_project */}
      {isScaffold && (
        <div className="space-y-2">
          <label
            htmlFor="project-name-input"
            className="block text-sm font-medium text-foreground"
          >
            Project Name <span className="text-red-500">*</span>
          </label>
          <Input
            id="project-name-input"
            aria-label="Project Name"
            placeholder="e.g. My App"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
          />
        </div>
      )}

      {/* Git URL */}
      <div className="space-y-2">
        <label
          htmlFor="git-url-input"
          className="block text-sm font-medium text-foreground"
        >
          Git URL{!isScaffold && <span className="text-red-500"> *</span>}
        </label>
        <Input
          id="git-url-input"
          aria-label="Git URL"
          placeholder="https://github.com/org/repo.git"
          value={gitUrl}
          onChange={(e) => setGitUrl(e.target.value)}
        />
      </div>

      {/* Branch — shown for non-scaffold tasks */}
      {!isScaffold && (
        <div className="space-y-2">
          <label
            htmlFor="branch-input"
            className="block text-sm font-medium text-foreground"
          >
            Branch{isReview ? <span className="text-red-500"> *</span> : " (optional)"}
          </label>
          <Input
            id="branch-input"
            aria-label="Branch"
            placeholder="e.g. main or feature/my-feature"
            value={branch}
            onChange={(e) => setBranch(e.target.value)}
          />
        </div>
      )}

      {/* Commits to Review — only for review_code */}
      {isReview && (
        <div className="space-y-2">
          <label
            htmlFor="commits-to-review-input"
            className="block text-sm font-medium text-foreground"
          >
            Commits to Review (optional)
          </label>
          <Input
            id="commits-to-review-input"
            aria-label="Commits to Review"
            type="number"
            min="1"
            placeholder="e.g. 5"
            value={commitsToReview}
            onChange={(e) => setCommitsToReview(e.target.value)}
          />
        </div>
      )}

      {/* Agent */}
      <div className="space-y-2">
        <label
          htmlFor="agent-select"
          className="block text-sm font-medium text-foreground"
        >
          Agent <span className="text-red-500">*</span>
        </label>
        <Select value={agentId} onValueChange={setAgentId}>
          <SelectTrigger id="agent-select" aria-label="Agent">
            <SelectValue placeholder="Select an agent" />
          </SelectTrigger>
          <SelectContent>
            {agents.map((a) => (
              <SelectItem key={a.id} value={a.id}>
                {a.display_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Requirements */}
      <div className="space-y-2">
        <label
          htmlFor="requirements-textarea"
          className="block text-sm font-medium text-foreground"
        >
          {reqConfig.label} <span className="text-red-500">*</span>
        </label>
        <Textarea
          id="requirements-textarea"
          aria-label={reqConfig.label}
          placeholder={reqConfig.placeholder}
          value={requirements}
          onChange={(e) => setRequirements(e.target.value)}
          rows={6}
        />
      </div>

      {/* Required Capabilities */}
      <div className="space-y-2">
        <label
          htmlFor="capabilities-input"
          className="block text-sm font-medium text-foreground"
        >
          Required Capabilities (optional)
        </label>
        <Input
          id="capabilities-input"
          aria-label="Required Capabilities"
          placeholder="e.g. python, git, docker"
          value={capabilitiesInput}
          onChange={(e) => setCapabilitiesInput(e.target.value)}
        />
        <p className="text-xs text-muted-foreground">
          Comma-separated list of sandbox capabilities needed for this task
        </p>
      </div>

      {/* Submit */}
      <Button type="submit" disabled={!isFormValid || isSubmitting}>
        {isSubmitting ? "Submitting..." : "Submit Task"}
      </Button>
    </form>
  );
}
