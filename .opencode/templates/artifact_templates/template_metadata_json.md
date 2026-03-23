# Example Artifact Metadata (.metadata.json)

This file is a JSON-formatted companion file that contains attribute information for each artifact.

```json
{
  "ArtifactType": "implementation_plan",
  "Summary": "A detailed design plan to add OAuth2 authentication. Includes modifications to auth.py and creation of a config file.",
  "LastEdited": "2024-03-19T23:50:00Z"
}
```

### Key Field Descriptions
- **`ArtifactType`**: Indicates the classification of the document (e.g., `task`, `implementation_plan`, `walkthrough`, `other`).
- **`Summary`**: A brief summary that helps the agent quickly grasp the core content of the document without reading it in full.
- **`LastEdited`**: A timestamp of when the artifact was last created or modified.

### ⚠️ Important: How to Generate Timestamp
**DO NOT hardcode the timestamp.** Always use the current UTC time when creating this file.

**Bash command:**
```bash
date +"%Y-%m-%dT%H:%M:%SZ"
```

This ensures the `LastEdited` field always reflects the actual creation/modification time.
