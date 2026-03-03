"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ProjectSummary } from "@/client/types.gen";

export interface TaskFormValues {
  project_type: "new" | "existing";
  project_id?: string;
  dev_agent_type: string;
  test_agent_type: string;
  requirements: string;
}

interface TaskFormProps {
  projects: ProjectSummary[];
  onSubmit: (data: TaskFormValues) => Promise<void>;
  initialValues?: Partial<TaskFormValues>;
  isSubmitting?: boolean;
}

const DEFAULT_VALUES: TaskFormValues = {
  project_type: "new",
  project_id: undefined,
  dev_agent_type: "spec_driven_development",
  test_agent_type: "generic_testing",
  requirements: "",
};

export function TaskForm({
  projects,
  onSubmit,
  initialValues,
  isSubmitting = false,
}: TaskFormProps) {
  const merged = { ...DEFAULT_VALUES, ...initialValues };

  // "project_select" is either "new" or a project UUID
  const getInitialProjectSelect = () => {
    if (merged.project_type === "existing" && merged.project_id) {
      return merged.project_id;
    }
    return "new";
  };

  const [projectSelect, setProjectSelect] = useState<string>(
    getInitialProjectSelect()
  );
  const [devAgentType, setDevAgentType] = useState<string>(
    merged.dev_agent_type
  );
  const [testAgentType, setTestAgentType] = useState<string>(
    merged.test_agent_type
  );
  const [requirements, setRequirements] = useState<string>(
    merged.requirements
  );

  const isProjectSelected = projectSelect !== "";
  const isRequirementsValid = requirements.trim().length > 0;
  const isFormValid = isProjectSelected && isRequirementsValid;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isFormValid || isSubmitting) return;

    const data: TaskFormValues =
      projectSelect === "new"
        ? {
            project_type: "new",
            project_id: undefined,
            dev_agent_type: devAgentType,
            test_agent_type: testAgentType,
            requirements,
          }
        : {
            project_type: "existing",
            project_id: projectSelect,
            dev_agent_type: devAgentType,
            test_agent_type: testAgentType,
            requirements,
          };

    await onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 max-w-2xl">
      {/* Project Selection */}
      <div className="space-y-2">
        <label
          htmlFor="project-select"
          className="block text-sm font-medium text-foreground"
        >
          Project
        </label>
        <Select
          value={projectSelect}
          onValueChange={setProjectSelect}
        >
          <SelectTrigger id="project-select" aria-label="Project">
            <SelectValue placeholder="Select a project" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="new">New Project</SelectItem>
            {projects.map((p) => (
              <SelectItem key={p.id} value={p.id}>
                {p.name ?? "Unnamed Project"}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Dev Agent Type */}
      <div className="space-y-2">
        <label
          htmlFor="dev-agent-select"
          className="block text-sm font-medium text-foreground"
        >
          Dev Agent
        </label>
        <Select
          value={devAgentType}
          onValueChange={setDevAgentType}
        >
          <SelectTrigger id="dev-agent-select" aria-label="Dev Agent">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="spec_driven_development">
              Spec Driven Development Agent
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Test Agent Type */}
      <div className="space-y-2">
        <label
          htmlFor="test-agent-select"
          className="block text-sm font-medium text-foreground"
        >
          Test Agent
        </label>
        <Select
          value={testAgentType}
          onValueChange={setTestAgentType}
        >
          <SelectTrigger id="test-agent-select" aria-label="Test Agent">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="generic_testing">Generic Testing Agent</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Requirements */}
      <div className="space-y-2">
        <label
          htmlFor="requirements-textarea"
          className="block text-sm font-medium text-foreground"
        >
          Requirements
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
      <Button
        type="submit"
        disabled={!isFormValid || isSubmitting}
      >
        {isSubmitting ? "Submitting..." : "Submit Task"}
      </Button>
    </form>
  );
}
