# Guide: Persistent Context

Persistent Context is the mechanism that allows the agent to remember not only the real-time conversation but also the **entire project history** and **project-specific rules**.

## Core Components
1.  **Conversation Logs**: Tracks past decisions and terminal outputs across dozens of interactions.
2.  **Project Rules (`AGENTS.md`)**: Constantly references the settings file in the current folder to understand "our coding style" or "our tech stack."
3.  **Artifact History**: Understands the project's current state by reviewing artifacts like `task.md` and `walkthrough.md`.

## How It Works
-   **Context Loading**: At the start of a session, the agent automatically gathers information about open files and previous errors.
-   **Real-time Reference**: It can understand ambiguous instructions like "the thing we talked about yesterday" by searching past logs to find the exact target.

## User Benefits
-   **Continuity**: The agent never loses context, even if the conversation is paused.
-   **Custom Collaboration**: The agent learns and applies different rules (`AGENTS.md`) for each project.
-   **Rapid Recovery**: In case of an error, it can find solutions by referencing its history of past successes.
