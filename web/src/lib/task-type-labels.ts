import type { TaskType } from "@/client/types.gen";

/**
 * Human-readable labels for task types.
 *
 * Used in the task list table (short form) and the task detail page (long form).
 * Both maps are kept here so labels stay consistent across the app.
 */
export const TASK_TYPE_LABELS: Record<TaskType, string> = {
  build_feature: "Build Feature",
  fix_bug: "Fix Bug",
  review_code: "Review Code",
  refactor_code: "Refactor Code",
  write_tests: "Write Tests",
  scaffold_project: "Scaffold Project",
};

export const TASK_TYPE_LABELS_LONG: Record<TaskType, string> = {
  build_feature: "Build a Feature",
  fix_bug: "Fix a Bug",
  review_code: "Review Code",
  refactor_code: "Refactor Code",
  write_tests: "Write Tests",
  scaffold_project: "Scaffold a Project",
};
