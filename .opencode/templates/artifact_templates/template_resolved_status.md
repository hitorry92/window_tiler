# Artifact State Management System (.resolved)

These files are an internal mechanism for tracking the **current work status** and **user approval** for a specific document.

### The Meaning of a `.resolved` File
- The existence of this file signifies that the work on the corresponding artifact is either **complete (Resolved)** or has received **final approval** from the user.
- For an `implementation_plan.md`, the creation of a `.resolved` file is a critical gate that allows the agent to safely proceed to the next phase.

### The Meaning of Numbers like `.resolved.0`
- This is an internal data structure for managing the **sequence of state changes** that occur during revisions and conversations.
- The agent uses this numbering to identify the latest state and maintain continuity in its work.
