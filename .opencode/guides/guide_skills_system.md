# Guide: Skills System

A Skill is a **specialized toolset** that allows an agent to act like an expert in a specific professional domain (e.g., n8n, Riot API, cloud infrastructure).

## Architecture
A Skill is a structured folder, not just a single file:
-   **`SKILL.md`**: The main document containing instructions and best practices for the skill.
-   **`scripts/`**: Dedicated script tools for automating tasks.
-   **`resources/`**: Templates, assets, and reference data.

## How It Works
1.  **Discovery**: The agent loads a skill when it determines it's needed to fulfill a user's request.
2.  **Adherence to Instructions**: It strictly follows the best practices and rules defined in `SKILL.md` when writing code.
3.  **Tool Utilization**: It uses the dedicated scripts to automate complex configurations or data processing.

## User Benefits
-   **Expertise on Demand**: The agent can immediately apply the latest techniques for a specific framework or tool.
-   **Error Reduction**: Human error is minimized by using proven methods and scripts.
-   **Complexity Management**: Even highly complex systems can be set up easily by following a skill's instructions.
