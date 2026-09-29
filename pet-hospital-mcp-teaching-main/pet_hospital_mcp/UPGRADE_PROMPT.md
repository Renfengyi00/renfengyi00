# Upgrade Prompt

Use this when adding phase-two tools.

You are extending `pet_hospital_mcp`, an MCP 2026-07-28 Streamable HTTP server built with the official Python SDK `mcp==2.0.0` and `MCPServer`.

Rules:

- Do not use or import `mcp.server.fastmcp.FastMCP`.
- Do not add old `initialize`, `Mcp-Session-Id`, session storage, session expiration, `max_sessions`, or stateful SSE resume behavior.
- Keep the Go Pet Hospital REST API as the only business backend.
- Add new tools under `src/pet_hospital_mcp/tools/`.
- Reuse `PetHospitalRestClient`, `ToolFailure`, `error_result`, JSON logging, and sensitive-field redaction.
- Keep MCP Streamable HTTP stateless with protocol version `2026-07-28`.
- Keep `/health`.
- Use Pydantic models for tool input, successful output, and structured error output.
- Reject unknown fields and invalid types at the MCP boundary.
- Map upstream failures to the existing error envelope:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "readable message",
    "details": {}
  }
}
```

Current phase-one tool:

- `list_pets`

Do not remove or rename it. New tools should be additive and covered by tests that avoid real backend access.
