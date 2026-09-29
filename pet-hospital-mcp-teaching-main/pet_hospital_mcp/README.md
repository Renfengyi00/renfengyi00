# Pet Hospital MCP

独立 Python MCP 服务，用于把仓库根目录已有的 Go 宠物医院 REST API 暴露给 AI Agent。

本服务只实现阶段一工具：`list_pets`。未实现阶段二工具。

## 技术栈

- Python 3.11+
- `mcp==2.0.0`
- MCP 协议版本：`2026-07-28`
- SDK API：`mcp.server.mcpserver.MCPServer`
- Transport：无状态 Streamable HTTP
- 默认 MCP 地址：`http://127.0.0.1:8787/mcp`
- 健康检查：`http://127.0.0.1:8787/health`

本项目没有使用或导入 `mcp.server.fastmcp.FastMCP`，也没有实现旧版 `initialize`、`Mcp-Session-Id` 会话、会话存储、会话过期、`max_sessions` 或有状态 SSE 恢复。

## 安装

先进入本目录：

```bash
cd pet_hospital_mcp
py -m pip install -e .[test]
```

如果你的系统 `python`/`pip` 已正确指向 Python 3.11+，也可以使用：

```bash
pip install -e .[test]
```

## 启动前置 Go REST API

MCP 服务只通过 HTTP 调用已有 Go 服务，不直接读写 `data/pet.db`。

在仓库根目录启动 Go 宠物医院服务：

```bash
cd ..
main.exe
```

或在安装 Go 1.22+ 后运行：

```bash
go run .
```

确认 Go 服务可访问：

```bash
curl http://127.0.0.1:8080/health
```

## 启动 MCP 服务

```bash
cd pet_hospital_mcp
py -m pet_hospital_mcp
```

可配置环境变量：

```bash
set MCP_HOST=127.0.0.1
set MCP_PORT=8787
set PET_HOSPITAL_BASE_URL=http://127.0.0.1:8080
py -m pet_hospital_mcp
```

PowerShell：

```powershell
$env:MCP_HOST = "127.0.0.1"
$env:MCP_PORT = "8787"
$env:PET_HOSPITAL_BASE_URL = "http://127.0.0.1:8080"
py -m pet_hospital_mcp
```

教学场景下没有实现认证、权限、CORS 或 Origin 校验。默认只监听 `127.0.0.1`。

## 端点

- MCP Streamable HTTP：`POST /mcp`
- 健康检查：`GET /health`

健康检查示例：

```bash
curl http://127.0.0.1:8787/health
```

响应示例：

```json
{
  "status": "ok",
  "service": "pet-hospital-mcp",
  "protocolVersion": "2026-07-28",
  "mcpPath": "/mcp",
  "backend": "http://127.0.0.1:8080"
}
```

## 工具

### list_pets

用途：查询宠物医院档案列表，支持搜索、过滤、排序和分页。

后端接口：`GET /api/v1/pets`

支持且仅支持这些参数：

`q`, `name`, `ownerName`, `ownerPhone`, `species`, `doctor`, `disease`, `status`, `min`, `max`, `sortBy`, `order`, `page`, `pageSize`

枚举值：

- `species`: `犬`, `猫`, `兔`, `鸟`, `仓鼠`, `爬宠`, `其他`
- `status`: `待就诊`, `就诊中`, `住院中`, `已康复`, `慢性病随访`
- `sortBy`: `id`, `name`, `ownerName`, `species`, `doctor`, `disease`, `status`, `totalCost`, `visitCount`, `createdAt`, `updatedAt`
- `order`: `asc`, `desc`

返回值对应 Go API 成功响应中的 `data`：

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "pageSize": 20,
  "totalPages": 0,
  "totalCost": 0
}
```

`items[].records` 和 `items[].charges` 兼容后端真实 JSON 中的 `null` 或数组。

## MCP 2026-07-28 HTTP 验证

2026-07-28 无状态请求不使用旧 `initialize`。每个请求都需要：

- `MCP-Protocol-Version: 2026-07-28`
- `Mcp-Method: <jsonrpc method>`
- 调用工具时还需要 `Mcp-Name: list_pets`
- JSON-RPC `params._meta` 携带协议版本和客户端能力

发现服务：

```bash
curl -s -X POST http://127.0.0.1:8787/mcp ^
  -H "Content-Type: application/json" ^
  -H "Accept: application/json" ^
  -H "MCP-Protocol-Version: 2026-07-28" ^
  -H "Mcp-Method: server/discover" ^
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"server/discover\",\"params\":{\"_meta\":{\"io.modelcontextprotocol/protocolVersion\":\"2026-07-28\",\"io.modelcontextprotocol/clientCapabilities\":{},\"io.modelcontextprotocol/clientInfo\":{\"name\":\"manual\",\"version\":\"0\"}}}}"
```

列出工具：

```bash
curl -s -X POST http://127.0.0.1:8787/mcp ^
  -H "Content-Type: application/json" ^
  -H "Accept: application/json" ^
  -H "MCP-Protocol-Version: 2026-07-28" ^
  -H "Mcp-Method: tools/list" ^
  -d "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\",\"params\":{\"_meta\":{\"io.modelcontextprotocol/protocolVersion\":\"2026-07-28\",\"io.modelcontextprotocol/clientCapabilities\":{},\"io.modelcontextprotocol/clientInfo\":{\"name\":\"manual\",\"version\":\"0\"}}}}"
```

调用 `list_pets`：

```bash
curl -s -X POST http://127.0.0.1:8787/mcp ^
  -H "Content-Type: application/json" ^
  -H "Accept: application/json" ^
  -H "MCP-Protocol-Version: 2026-07-28" ^
  -H "Mcp-Method: tools/call" ^
  -H "Mcp-Name: list_pets" ^
  -d "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{\"_meta\":{\"io.modelcontextprotocol/protocolVersion\":\"2026-07-28\",\"io.modelcontextprotocol/clientCapabilities\":{},\"io.modelcontextprotocol/clientInfo\":{\"name\":\"manual\",\"version\":\"0\"}},\"name\":\"list_pets\",\"arguments\":{\"species\":\"犬\",\"page\":1,\"pageSize\":10}}}"
```

MCP Inspector 或 SDK 2.x 客户端验证时，使用 Streamable HTTP 地址：

```text
http://127.0.0.1:8787/mcp
```

客户端应执行 `server/discover`，再 `tools/list`，然后 `tools/call`。不要发送旧版 `initialize`。

## 错误格式

工具调用失败通过 MCP 2.x `CallToolResult` 的 `isError: true` 标记，并返回统一结构：

```json
{
  "error": {
    "code": "BACKEND_TIMEOUT",
    "message": "The Go pet hospital API timed out.",
    "details": {}
  }
}
```

错误码：

- `VALIDATION_ERROR`
- `BACKEND_TIMEOUT`
- `BACKEND_UNAVAILABLE`
- `BACKEND_API_ERROR`
- `BACKEND_INVALID_RESPONSE`
- `INTERNAL_ERROR`

## 测试

测试不访问真实 Go 服务，使用 `httpx.MockTransport` 和 ASGI transport。

```bash
cd pet_hospital_mcp
pytest -q
```

预期结果：

```text
24 passed
```
