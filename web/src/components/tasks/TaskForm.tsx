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
import type { AgentResponse } from "@/client/types.gen";

export interface TaskFormValues {
  project_type: "new" | "existing";
  project_name?: string;
  agent_id: string;
  git_url?: string;
  branch?: string;
  requirements: string;
}

interface TaskFormProps {
  agents: AgentResponse[];
  onSubmit: (data: TaskFormValues) => Promise<void>;
  initialValues?: Partial<TaskFormValues>;
  isSubmitting?: boolean;
}

const DEFAULT_VALUES: TaskFormValues = {
  project_type: "new",
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

  const [projectType, setProjectType] = useState<"new" | "existing">(
    merged.project_type
  );
  const [projectName, setProjectName] = useState<string>(
    merged.project_name ?? ""
  );
  const [agentId, setAgentId] = useState<string>(merged.agent_id ?? "");
  const [gitUrl, setGitUrl] = useState<string>(merged.git_url ?? "");
  const [branch, setBranch] = useState<string>(merged.branch ?? "");
  const [requirements, setRequirements] = useState<string>(
    merged.requirements
  );

  const isExisting = projectType === "existing";

  const isProjectNameValid = !isExisting ? projectName.trim().length > 0 : true;
  const isGitUrlValid = isExisting ? gitUrl.trim().length > 0 : true;
  const isAgentSelected = agentId.trim().length > 0;
  const isRequirementsValid = requirements.trim().length > 0;
  const isFormValid =
    isProjectNameValid && isGitUrlValid && isAgentSelected && isRequirementsValid;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isFormValid || isSubmitting) return;

    const data: TaskFormValues = {
      project_type: projectType,
      project_name: isExisting ? undefined : projectName.trim(),
      agent_id: agentId,
      git_url: gitUrl.trim() || undefined,
      branch: branch.trim() || undefined,
      requirements,
    };

    await onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 max-w-2xl">
      {/* Project Type */}
      <div className="space-y-2">
        <label
          htmlFor="project-type-select"
          className="block text-sm font-medium text-foreground"
        >
          Project
        </label>
        <Select
          value={projectType}
          onValueChange={(v) => {
            setProjectType(v as "new" | "existing");
            setGitUrl("");
          }}
        >
          <SelectTrigger id="project-type-select" aria-label="Project type">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="new">New Project</SelectItem>
            <SelectItem value="existing">Existing Project</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Project Name — only for new projects */}
      {!isExisting && (
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
          Git URL{isExisting && <span className="text-red-500"> *</span>}
        </label>
        <Input
          id="git-url-input"
          aria-label="Git URL"
          placeholder="https://github.com/org/repo.git"
          value={gitUrl}
          onChange={(e) => setGitUrl(e.target.value)}
        />
      </div>

      {/* Branch (only for existing projects) */}
      {isExisting && (
        <div className="space-y-2">
          <label
            htmlFor="branch-input"
            className="block text-sm font-medium text-foreground"
          >
            Branch (optional)
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
          Requirements <span className="text-red-500">*</span>
        </label>
        <Textarea
          id="requirements-textarea"
          aria-label="Requirements"
          placeholder="Describe what you want to build..."
          value={requirements}
          onChange={(e) => setRequirements(e.target.value)}
          rows={6}
        />
      </div>

      {/* Submit */}
      <Button type="submit" disabled={!isFormValid || isSubmitting}>
        {isSubmitting ? "Submitting..." : "Submit Task"}
      </Button>
    </form>
  );
}
