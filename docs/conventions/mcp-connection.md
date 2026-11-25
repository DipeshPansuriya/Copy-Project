# MCP Connection

## 1. Overview

OpenClipboard does not currently expose an MCP (Model Context Protocol) server. The HTTP API at `/api/` is the primary integration surface.

## 2. Future MCP Server (Planned)

If an MCP server is added, it would expose tools such as:

| Tool | Description |
|------|-------------|
| `clipboard_send` | Send text or file and get a code |
| `clipboard_retrieve` | Retrieve content by code |
| `clipboard_delete` | Delete content by code |
| `clipboard_stats` | Get active item stats |

### Example MCP Tool Definition

```json
{
  "name": "clipboard_send",
  "description": "Send text to OpenClipboard and get a 12-character retrieval code",
  "inputSchema": {
    "type": "object",
    "properties": {
      "text": { "type": "string" },
      "ttl": { "type": "integer", "default": 900 },
      "one_shot": { "type": "boolean", "default": false }
    },
    "required": ["text"]
  }
}
```

## 3. Connection Details (Future)

| Field | Value |
|-------|-------|
| Transport | stdio or HTTP |
| Endpoint | `http://localhost:8000/api/` |
| Auth | None (code-based capability) |

## 4. Current Integration

Until MCP is implemented, use `curl` or any HTTP client to interact with the API directly.
