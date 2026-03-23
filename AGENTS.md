# Project Guidelines (AGENTS.md v5)

This file defines the **paramount rules and context** for all AI agents operating in this project. The instructions in this document **override** any other configuration files.

---

## 0. Common Meta-Rules

- **Language**:
  - All conversational messages, summaries, and explanations directed at the user **MUST be in Korean.**
  - Code, logs, and raw outputs from external tools **MUST remain in their original language (usually English).** Add explanations in Korean if necessary.
- **Working Directory**:
  - Always operate based on the **project root directory.**
- **Guide Caching**:
  - In a single session, once a guide file has been read and understood, you **do not need to read the entire file again** unless its content has changed.
  - If a file path or modification time change is detected, re-read the latest version to update your understanding.

---

## 1. Pre-Task Procedures

When starting a new task (i.e., when a new goal, ticket, or explicit "to-do" is assigned), you **MUST follow the sequence below.**

### 1.1 Agent Workflow Guide

All tasks MUST read and understand `.opencode/workflows/agent_workflow_guide.md`.

**Rules:**

1. If you have not yet read this file in the current session, you **MUST read and understand it before formulating a task plan.**
2. If you have already read it but suspect it has been changed or versioned, re-read it to refresh your understanding.
3. If the file is inaccessible or a read error occurs:
   - Notify the user in Korean.
   - Proceed **conservatively** with the task based on known workflow patterns and the rules in this `AGENTS.md`.

For the detailed directory structure and workflow steps, refer to the `.opencode/workflows/agent_workflow_guide.md` document.

---

## 2. Task Type and Artifact Management

### 2.1 Task Type Taxonomy

When you recognize a new task, first select **one task type** from the list below. Concrete examples are provided to improve classification accuracy.

- `add_feature`: Adding new functionality.
  - *Example: "Add a new `/api/v1/users` endpoint with JWT auth."*
- `fix_bug`: Fixing broken behavior, errors, or bugs.
  - *Example: "Fix the TypeError that occurs during `npm test`."*
- `refactor_code`: Improving structure/quality without adding functionality.
  - *Example: "Migrate the database connection logic from callbacks to async/await."*
- `write_docs`: Writing/supplementing documentation, READMEs, guides, etc.
- `research`: External investigation, comparative analysis, design review.
- `config_ops`: Changes related to configuration, deployment, or CI/CD scripts.
  - *Example: "Update the Dockerfile to use a smaller base image."*
- If it doesn't clearly fit, choose the closest type and add clarification in the description.

The chosen task type becomes the **basis for Knowledge Item retrieval and planning.**

### 2.2 Artifact Management (CRITICAL)

When writing artifact (.md) files, you **MUST** read `.opencode/guides/artifact_management_guide.md` and follow its rules strictly.

**All .md files are artifacts.** This includes:
- Standard artifacts: `task.md`, `implementation_plan.md`, `walkthrough.md`
- Project documentation: `README.md`
- Guides and other markdown files

**MANDATORY 3-LAYER RULE:**
1. Whenever you create or modify an artifact `.md` file, you **MUST IMMEDIATELY** create/update its corresponding `.metadata.json` file.
2. You **MUST NEVER** create a `.resolved` file until the user explicitly approves the artifact.

All task-related artifacts are primary communication tools with the user, so their content **MUST be written in Korean** (per the top-level language rule).

---

## 3. Shared Workspace, Context Alignment, and Approval Gating

### 3.1 Shared Workspace Protocol
- All agents **MUST** use the `.opencode/active_work/` directory as a shared workspace.
- Before starting a new task, you **MUST** scan for existing artifacts to check for conflicting or related work and read them to align your context.
- You **MUST NOT** arbitrarily overwrite content written by other agents. Clearly document your changes or additions.

### 3.2 User Approval Principle - CRITICAL SAFETY RULE
- You **MUST NOT** proceed to the execution phase of any planned task without **explicit and direct approval from the user.**
- The specific technical method for verifying and proving the approval status is governed by the rules in `.opencode/guides/artifact_management_guide.md`.

---

## 4. Situational Guide Usage Rules

During your work, if the situations below arise, you **must read the corresponding guide before** proceeding with the related task.

- **Regarding Skill usage/creation**:
  - `.opencode/guides/guide_skills_system.md`
- **Regarding memory/context management**:
  - `.opencode/guides/guide_persistent_context.md`
- **Regarding external research/investigation**:
  - `.opencode/workflows/guide_notebooklm_research.md`

**Common Rules:**
- If you have already read the same guide in the same session and the file has not changed, you do not need to read the entire file again.
- If a guide file is missing or a read error occurs:
  - Notify the user of the situation.
  - Work in the **most conservative manner** based on this `AGENTS.md` and your existing workflow knowledge.

---

## 5. Autonomous Knowledge Reuse (Knowledge Items)

When starting a new task (especially during the **planning phase**), leverage past successes by following the procedure below.

### 5.1 Knowledge Item Retrieval Path

- The default location for the global KI repository is:
  - `C:/Users/SEUNGIN/.config/opencode/knowledge_items/by_task_type/`
- To ensure portability across different environments, follow this sequence:
  1. If the environment variable `OPENCODE_KI_ROOT` is set, prioritize using `${OPENCODE_KI_ROOT}/by_task_type/`.
  2. If not, attempt to use the default path above.
- If neither path is accessible:
  - Notify the user of the fact.
  - Formulate a plan from **first principles** without KI.

### 5.2 Retrieval Procedure

1. Based on the `task type` selected in section 2.1, search the corresponding directory for KIs.
2. Prioritize KIs that are similar to the task's subject (e.g., file paths, domain, tech stack keywords).
3. If a relevant KI is found:
   - Read the KI to understand its success/failure avoidance patterns.
   - Use it as a **primary reference** when creating the `implementation_plan.md`.
4. If no suitable KI is found, or if it's too outdated or clearly incompatible with the current architecture:
   - Create a **new plan based on the current context** without referencing the KI.
   - If necessary, leave sufficient explanation in the `walkthrough.md` so that this task's result can be considered as a candidate for a new KI.

---

## 6. Workflow Overview (Summary)

In every task, the agent must follow this **high-level flow**:

1.  **Task Recognition**
    -   Read the user request/ticket/goal and determine the `task type`.
2.  **Mandatory Guide Check**
    -   Verify that the required guides from section 1.1 (and situational guides) have been read and update context with the latest versions if necessary.
3.  **Existing Context Check**
    -   Explore relevant artifacts in `.opencode/active_work/` to check for ongoing related tasks.
4.  **Knowledge Item Utilization**
    -   Search for KIs based on the `task type` and subject, and gather usable patterns.
5.  **Artifact Creation & Planning**
    -   Create/Update `task.md` → Organize goals/scope/checklist.
    -   Create/Update `implementation_plan.md` → Detail the design and steps.
6.  **Implementation & Verification**
    -   Modify/write code and perform tests according to the plan.
7.  **Result Summarization**
    -   Record the actual work done, test results, and remaining risks in `walkthrough.md`.
    -   Provide a summary to the user in Korean.

---

## 7. Important Notes

-   If the contents of this `AGENTS.md` become misaligned with the project's structure, architecture, or toolchain, you **must first update this file** before instructing agents to follow the new rules.
-   **An agent confidently following outdated/wrong rules** can be more dangerous than one with no rules. Therefore, when making changes to architecture, directory structures, or build/test commands, update `AGENTS.md` accordingly.
