# AI Agent Collaboration: The 3-Phase Standard Workflow

This guide describes the **standard collaboration process** for an AI agent and a user to follow when undertaking large-scale projects or complex coding tasks. This system is designed to ensure transparency, safety, and the quality of the results.

---

## Phase 1: PLANNING
**Objective:** To clearly define "what to solve and how to solve it" and reach an agreement with the user.

### Task Granularity
> **Breaking work into small units is the most important principle.**

- Do not treat "implement entire project" as a single task.
- Instead, divide work into **small and clear units** like "Implement basic UI layout" or "Add window resize logic".
- Complete one cycle for each small completed task.
- **If a cycle feels too long, break it down into smaller cycles.**

### Key Artifacts
- **`task.md` (Checklist)**: Hierarchically manages milestones and detailed items for the entire task. It's a "living document" that the agent and user review together until the work is complete. [👉 See Template](../templates/artifact_templates/template_task.md)
- **`implementation_plan.md` (Implementation Plan)**: The technical design document. It specifies affected files, architectural changes, and potential risks and mitigation strategies. [👉 See Template](../templates/artifact_templates/template_implementation_plan.md)

### Working Procedures
1.  **Workspace Preparation:** All artifacts are to be created and managed within a task-specific directory formatted as `.opencode/active_work/[YYYY-MM-DD_task_name]/`.
2.  **Continuity Check:** Before starting a new task, you must check if artifacts for the same task already exist. If so, they must be read first to understand the current state and maintain continuity.


### Collaboration Points
- Each artifact (`task.md`, `implementation_plan.md`, `walkthrough.md`) **MUST be separately approved by the user** before creating the corresponding `.resolved` file.
- The user reviews each artifact to provide **feedback** or **approval**.
- This ensures that the agent and user are aligned on the same goal before any complex logic is modified.
- **Only after user approval** can the `.resolved` file be created, enabling version control and proceeding to the next phase.
- **Synchronization Rule**: When `implementation_plan.md` is modified, the agent **MUST also review and update `task.md`** to reflect the changes. Task items must match the implementation details.

---

## Phase 2: EXECUTION
**Objective:** To actually build the system and write code according to the approved plan.

### Pre-Implementation Checklist (MANDATORY)
Before writing ANY code, verify ALL of the following:
- [ ] Verify that `task.md` has received **final approval** from the user.
- [ ] Verify that `implementation_plan.md` has received **final approval** from the user.
- [ ] Current task items in `task.md` are checked off.
- [ ] Implementation plan details match `task.md` items.
- [ ] If adding new features, update the planning documents (`task.md`, `implementation_plan.md`) first and **obtain user approval** before starting to code.

> **Note:** The specific technical method for verifying an artifact's "approval" state is governed by the rules in `.opencode/guides/artifact_management_guide.md`.

**IF ANY CHECKPOINT IS MISSING: DO NOT WRITE CODE. Report to user and wait for approval.**

### Key Activities
- The agent solves items from `task.md` one by one, updating their status in real time.
- **Iterative Refinement**: Instead of modifying a large amount of code at once, it makes precise changes divided by functional units.
- **Real-time Feedback Loop**: If unexpected technical constraints are discovered during implementation, the agent immediately reports to the user and revises the plan.

---

## Phase 3: VERIFICATION
**Objective:** To ensure the quality of the final product and formally report the work that was done.

### Key Artifacts
- **`walkthrough.md` (Completion Report)**: A summary report of the final work results. It describes what was changed, which tests were passed, and where the final deliverables are located. [👉 See Template](../templates/artifact_templates/template_walkthrough.md)

### Key Activities
- **Testing and Debugging**: Technically proves functionality through syntax checks, unit tests, and integration tests.
- **Proof of Work**: Allows the user to visually confirm the results through terminal logs, screenshots, or video recordings.

### The `walkthrough.md` Principle: Proof of "Completion," Not "Perfection"
The `walkthrough.md` is not a report on the "perfect final product," but rather a document that proves **"the plan agreed upon for this cycle (`implementation_plan.md`) has been faithfully executed."**

- **Accountability to the Plan**: If the functionality works correctly within the scope of the work agreed upon in the `implementation_plan.md`, then the goal for the current cycle is achieved. The `walkthrough.md` serves to confirm: "Yes, the promised parts have been implemented as planned and are working correctly."
- **Incremental Improvement**: If the result works as planned but is unsatisfactory in practice or requires further enhancement, that becomes the subject of a **"new work cycle."** The correct workflow is to neatly conclude the current work with a `walkthrough.md` and then plan the next improvement with a new version of `task.md` and `implementation_plan.md`.
- **Recording Small Wins**: This approach reduces the pressure to solve everything at once and allows for the accumulation of **"small, verifiable successes"** step by step. A `walkthrough.md` is the report that chronicles each of these small wins.

In conclusion, if the planned objectives have been met and the features are functioning correctly within that scope, it is the correct procedure to write a `walkthrough.md` to clearly close the current cycle, regardless of any additional requirements.

### Cycle Completion
- **Each workflow cycle** (Phase 1 → Phase 2 → Phase 3) **generates a walkthrough.md**.
- When user requests new features, a **new cycle begins** with updated `task.md` and `implementation_plan.md`.
- A **new walkthrough.md** is created for each completed cycle.

---

### **4. Artifact Management**
For specific rules on creating, versioning, and approving work artifacts (task.md, implementation_plan.md, etc.), refer to the `.opencode/guides/artifact_management_guide.md` document.

