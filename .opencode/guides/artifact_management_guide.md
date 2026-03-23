# Guide: Artifact Management Protocol

## 1. The Technical Definition of 'Approval'
In the workflow, the 'Approved' state is proven **only by the physical existence of a `.resolved` or `.resolved.n` file.**

- **Explicit Rule:** An artifact is considered 'Approved' only if a corresponding `.resolved` file exists in the same directory.
- **Prohibition:** An agent **MUST NEVER** infer approval based on conversational context or nuance. The existence of the `.resolved` file is the Single Source of Truth.
- **Execution Prerequisite:** You **MUST NOT** proceed to the EXECUTION phase of any task until the corresponding `implementation_plan.md.resolved` file exists.
- **Creation Condition:** You **MUST** create a `.resolved` file for an artifact only after receiving **explicit, direct approval** from the user for that specific artifact.
- **Verification Step:** If you believe approval has been given but the `.resolved` file is missing, you **MUST** ask the user for explicit confirmation before creating the file and proceeding.

---

*All task artifacts (`.md`) MUST have a 3-layer structure (content, metadata, state snapshot). The agent MUST follow this procedure **absolutely without exception** when creating or modifying artifacts.*

---

## 2. Artifact Lifecycle Principles

### 2.1 Metadata (`.metadata.json`)
This file serves as the **'Latest Summary (Latest Header)'**.
- **Purpose**: Used for quickly understanding the current status (type, summary) of the artifact.
- **Update Condition**: Only update when the **content of the `.md` file changes**. Do NOT update when a `.resolved` file is created.
- **Overwrite Rule**: When the content file is modified, both `Summary` and `LastEdited` fields **MUST be overwritten together** to maintain the latest state. This file does not accumulate historical records.

### 2.2 State Snapshot (`.resolved.n`)
These files serve as the **'Version Log'**.
- **Purpose**: The existence of `.resolved`, `.resolved.0`, `.resolved.1`, etc., represents the history of user consensus.
- **Version Creation Rules:**
    1. **Initial Creation**: When an artifact is first created, only `.metadata.json` is generated (no `.resolved` yet).
    2. **First Approval**: If the user approves, create `.resolved` (no number suffix).
    3. **Subsequent Approvals**: When the `.md` file is modified and approved again, create `.resolved.0`. The next time becomes `.resolved.1`, and so on. **DO NOT overwrite** the previous `.resolved` file.
- **Significance**: This allows tracking the history of "which plan was approved at which point."

---

## 3. Artifact Creation and Approval Procedures

### 3.1 Creating New Artifacts
1.  **Template Lookup:** Read the artifact templates from `.opencode/templates/artifact_templates/`.
2.  **Simultaneous File Creation:**
    - Create the **content file** (`[artifact_name].md`) using Write.
    - Immediately create the **metadata file** (`[artifact_name].md.metadata.json`).
    - **DO NOT** create the `.resolved` file at this time.

### 3.2 After Artifact Approval (`.resolved` Creation Rules)
All artifacts MUST be explicitly approved by the user, and the corresponding `.resolved` file is created upon approval.

| Artifact | Approval Timing | Required |
|---|---|---|
| `task.md` | After work scope/checklist finalization | Required |
| `implementation_plan.md` | After technical design/plan approval | **Required** (EXECUTION starts after approval) |
| `walkthrough.md` | After completion report final confirmation | Required |

**Procedure:**
1.  When explicit approval is received from the user, Read the final content of the artifact.
2.  Write that content to a **new version of the `.resolved.n` file**. (e.g., `.resolved` if none exists, otherwise `.resolved.0`)
3.  **Important**: The EXECUTION phase can only begin when `implementation_plan.md.resolved` exists.
