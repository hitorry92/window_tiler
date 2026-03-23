# Project Guidelines (AGENTS.md v2)

This file defines the **paramount rules and context** for all AI agents operating in this project. The instructions in this document **override** any other configuration files.

---

## 0. Common Meta-Rules

-   **Language**:
    -   All conversational messages, summaries, and explanations directed at the user **MUST be in Korean.**
    -   Code, logs, and raw outputs from external tools **MUST remain in their original language (usually English).** Add explanations in Korean if necessary.
-   **Working Directory**:
    -   Always operate based on the **project root directory.**
-   **Guide Caching**:
    -   In a single session, once a guide file has been read and understood, you **do not need to read the entire file again** unless its content has changed.
    -   If a file path or modification time change is detected, re-read the latest version to update your understanding.


---

---

## 1. Mandatory Pre-Task Procedures

When starting a new task (i.e., when a new goal, ticket, or explicit "to-do" is assigned), you **MUST follow the sequence below.**

### 1.1 Read Foundational Guides

The following two files are the **core guides that form the basis of all tasks**:

-   `.opencode/workflows/agent_workflow_guide.md`
-   `.opencode/guides/artifact_management_guide.md`

**Rules:**

1.  If you have not yet read these two files in the current session, you **MUST read and understand them before formulating a task plan.**
2.  If you have already read them but suspect they have been changed or versioned, re-read them to refresh your understanding.
3.  If a file is inaccessible or a read error occurs:
    -   Notify the user of the fact in Korean.
    -   Proceed **conservatively** with the task based on known workflow patterns and the rules in this `AGENTS.md`.


---

---

## 2. Task Type and Artifact Management

### 2.1 Task Type Taxonomy

When you recognize a new task, first select **one task type** from the list below. Concrete examples are provided to improve classification accuracy.

-   `add_feature`: Adding new functionality.
    -   *Example: "Add a new `/api/v1/users` endpoint with JWT auth."*
-   `fix_bug`: Fixing broken behavior, errors, or bugs.
    -   *Example: "Fix the TypeError that occurs during `npm test`."*
-   `refactor_code`: Improving structure/quality without adding functionality.
    -   *Example: "Migrate the database connection logic from callbacks to async/await."*
-   `write_docs`: Writing/supplementing documentation, READMEs, guides, etc.
-   `research`: External investigation, comparative analysis, design review.
-   `config_ops`: Changes related to configuration, deployment, or CI/CD scripts.
    -   *Example: "Update the Dockerfile to use a smaller base image."*
-   If it doesn't clearly fit, choose the closest type and add clarification in the description.

The chosen task type becomes the **basis for Knowledge Item retrieval and planning.**

### 2.2 Standard Artifacts & Directory Structure

All tasks are managed using three standard artifacts within a dedicated task directory. As these are primary communication tools with the user, their content **MUST be written in Korean**, in accordance with the top-level language rule. The directory should be named with a date and a short, descriptive title.

**Example Directory Structure:**
```
.opencode/active_work/
└── 2026-03-20_add_user_endpoint/
    ├── task.md
    ├── implementation_plan.md
    └── walkthrough.md
```

**Artifact-Creation Lifecycle:**

1.  **At the start of Planning**:
    -   Create the `[YYYY-MM-DD_task_name]/` directory.
    -   Create `task.md` inside it, recording a summary, the task type, and `status: in_progress`.
2.  **Once the design/plan is clear**:
    -   Create `implementation_plan.md` in the same directory.
3.  **After task completion**:
    -   Create `walkthrough.md` in the same directory.

If artifacts for the same task already exist, read them first to understand the current state and maintain **continuity**.


---

---

## 3. Shared Workspace, Context Alignment, and Approval Gating

### 3.1 Shared Workspace Protocol
-   All agents **MUST** use the `.opencode/active_work/` directory as a shared workspace.
-   Before starting a new task, you **MUST** scan for existing artifacts to check for conflicting or related work and read them to align your context.
-   You **MUST NOT** arbitrarily overwrite content written by other agents. Clearly document your changes or additions.

### 3.2 State Layer Adherence (.resolved) - CRITICAL SAFETY RULE
The State Layer (`.resolved` files) is the **only acceptable signal** for user approval. This rule is non-negotiable.

-   You **MUST NOT** proceed to the EXECUTION phase of any task until the corresponding `implementation_plan.md.resolved` file exists.
-   You **MUST** create a `.resolved` file for an artifact only after receiving **explicit, direct approval** from the user for that specific artifact. Do not infer approval from conversational cues.
-   If you believe approval has been given but the `.resolved` file is missing, you **MUST** ask the user for explicit confirmation before creating the file and proceeding.


---

---

## 4. Situational Guide Usage Rules

During your work, if the situations below arise, you **must read the corresponding guide before** proceeding with the related task.

-   **Regarding Skill usage/creation**:
    -   `.opencode/guides/guide_skills_system.md`
-   **Regarding memory/context management**:
    -   `.opencode/guides/guide_persistent_context.md`
-   **Regarding external research/investigation**:
    -   `.opencode/workflows/guide_notebooklm_research.md`

**Common Rules:**
-   If you have already read the same guide in the same session and the file has not changed, you do not need to read the entire file again.
-   If a guide file is missing or a read error occurs:
    -   Notify the user of the situation.
    -   Work in the **most conservative manner** based on this `AGENTS.md` and your existing workflow knowledge.


---

---

## 5. Autonomous Knowledge Reuse (Knowledge Items)

When starting a new task (especially during the **planning phase**), leverage past successes by following the procedure below.

### 5.1 Knowledge Item Retrieval Path

-   The default location for the global KI repository is:
    -   `C:/Users/SEUNGIN/.config/opencode/knowledge_items/by_task_type/`
-   To ensure portability across different environments, follow this sequence:
    1.  If the environment variable `OPENCODE_KI_ROOT` is set, prioritize using `${OPENCODE_KI_ROOT}/by_task_type/`.
    2.  If not, attempt to use the default path above.
-   If neither path is accessible:
    -   Notify the user of the fact.
    -   Formulate a plan from **first principles** without KI.

### 5.2 Retrieval Procedure

1.  Based on the `task type` selected in section 2.1, search the corresponding directory for KIs.
2.  Prioritize KIs that are similar to the task's subject (e.g., file paths, domain, tech stack keywords).
3.  If a relevant KI is found:
    -   Read the KI to understand its success/failure avoidance patterns.
    -   Use it as a **primary reference** when creating the `implementation_plan.md`.
4.  If no suitable KI is found, or if it's too outdated or clearly incompatible with the current architecture:
    -   Create a **new plan based on the current context** without referencing the KI.
    -   If necessary, leave sufficient explanation in the `walkthrough.md` so that this task's result can be considered as a candidate for a new KI.


---

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

---

## 7. Code Verification & Testing Protocol

When modifying code, the agent **MUST** perform self-verification before relying on user testing.

### 7.1 Pre-Implementation Verification

Before writing/editing code, verify:

1.  **Logic Flow Analysis**:
    - Trace through all code paths (if/else branches, loops)
    - Check for variables that might be overwritten after modification
    - Verify data update order (what gets updated first/last)

2.  **State Consistency Check**:
    - When modifying shared state (e.g., `profiles`, `config`, class attributes), verify that all places reading that state are updated appropriately
    - Check for "read-after-write" issues where a value is set but immediately overwritten

3.  **Event Handler Verification**:
    - For GUI code: verify event binding and handler execution order
    - For callback functions: verify parameter passing and return value handling

### 7.2 Post-Implementation Verification

After code modification:

1.  **Syntax Check**:
    - Run `python -m py_compile <file.py>` to verify no syntax errors

2.  **Import Check**:
    - Verify all imported modules are available

3.  **Logic Walkthrough**:
    - Manually trace through the modified code with example inputs
    - Identify any "off-by-one" errors, boundary conditions, or unhandled edge cases

### 7.3 Common Bug Patterns to Avoid

| Pattern | Problem | Solution |
|---------|---------|----------|
| Read-after-write | Value set in handler, then overwritten in update function | Update source of truth (profiles/config) before calling update |
| Scope isolation | Inner function uses stale closure variable | Use mutable container (list/dict) or pass as parameter |
| Event handler collision | Multiple handlers for same event | Verify only one handler processes the event |
| Missing state propagation | State updated but UI not refreshed | Call refresh/update functions after state change |

### 7.4 When User Testing is Required

User testing is **required** only for:
- Actual visual rendering results (GUI appearance)
- System integration (OS-level APIs)
- Timing-dependent behavior (animations, async operations)
- Real-time user interaction patterns

**Before asking user to test**, the agent should:
1. Complete self-verification (Section 7.1-7.2)
2. Fix any identified issues proactively
3. Provide specific test scenarios and expected outcomes

---

---

## 8. Important Notes

-   If the contents of this `AGENTS.md` become misaligned with the project's structure, architecture, or toolchain, you **must first update this file** before instructing agents to follow the new rules.
-   **An agent confidently following outdated/wrong rules** can be more dangerous than one with no rules. Therefore, when making changes to architecture, directory structures, or build/test commands, update `AGENTS.md` accordingly.
