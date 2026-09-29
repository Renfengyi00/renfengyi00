from __future__ import annotations

from typing import Any

import httpx
import pytest

from pet_hospital_mcp.config import Settings
from pet_hospital_mcp.rest_client import PetHospitalRestClient
from pet_hospital_mcp.server import MCP_PATH, PROTOCOL_VERSION, create_app, create_server
from pet_hospital_mcp.tools.list_pets import ListPetsOutput


class FakeRestClient:
    base_url = "http://backend.test"

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def list_pets(self, params: Any) -> ListPetsOutput:
        self.calls.append(params.model_dump(exclude_none=True))
        return ListPetsOutput.model_validate(
            {
                "items": [],
                "total": 0,
                "page": params.page,
                "pageSize": params.pageSize,
                "totalPages": 0,
                "totalCost": 0,
            }
        )


def settings() -> Settings:
    return Settings(pet_hospital_base_url="http://backend.test")


def meta() -> dict[str, Any]:
    return {
        "io.modelcontextprotocol/protocolVersion": PROTOCOL_VERSION,
        "io.modelcontextprotocol/clientCapabilities": {},
        "io.modelcontextprotocol/clientInfo": {"name": "pytest", "version": "0"},
    }


def headers(method: str, name: str | None = None) -> dict[str, str]:
    out = {
        "content-type": "application/json",
        "accept": "application/json",
        "MCP-Protocol-Version": PROTOCOL_VERSION,
        "Mcp-Method": method,
    }
    if name is not None:
        out["Mcp-Name"] = name
    return out


@pytest.mark.asyncio
async def test_tool_registration_name_and_schema() -> None:
    server = create_server(settings(), FakeRestClient())  # type: ignore[arg-type]
    tools = await server.list_tools()

    assert [tool.name for tool in tools] == ["list_pets"]
    schema = tools[0].input_schema
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == {
        "q",
        "name",
        "ownerName",
        "ownerPhone",
        "species",
        "doctor",
        "disease",
        "status",
        "min",
        "max",
        "sortBy",
        "order",
        "page",
        "pageSize",
    }
    assert schema["properties"]["species"]["anyOf"][0]["enum"] == ["犬", "猫", "兔", "鸟", "仓鼠", "爬宠", "其他"]


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    app = create_app(settings(), FakeRestClient())  # type: ignore[arg-type]
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["protocolVersion"] == PROTOCOL_VERSION


@pytest.mark.asyncio
async def test_stateless_discover_and_call_list_pets_over_http() -> None:
    fake = FakeRestClient()
    app = create_app(settings(), fake)  # type: ignore[arg-type]

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            discover = await client.post(
                MCP_PATH,
                headers=headers("server/discover"),
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "server/discover",
                    "params": {"_meta": meta()},
                },
            )
            tools = await client.post(
                MCP_PATH,
                headers=headers("tools/list"),
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {"_meta": meta()},
                },
            )
            call = await client.post(
                MCP_PATH,
                headers=headers("tools/call", "list_pets"),
                json={
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "_meta": meta(),
                        "name": "list_pets",
                        "arguments": {"species": "犬", "page": 2, "pageSize": 5},
                    },
                },
            )

    assert discover.status_code == 200
    assert discover.json()["result"]["supportedVersions"] == [PROTOCOL_VERSION]
    assert "Mcp-Session-Id" not in discover.headers
    assert tools.status_code == 200
    assert tools.json()["result"]["tools"][0]["name"] == "list_pets"
    assert call.status_code == 200
    payload = call.json()["result"]
    assert payload["isError"] is False
    assert payload["structuredContent"]["page"] == 2
    assert fake.calls == [{"page": 2, "pageSize": 5, "species": "犬"}]
    assert "Mcp-Session-Id" not in call.headers


@pytest.mark.asyncio
async def test_http_tool_validation_error_is_structured_error_result() -> None:
    app = create_app(settings(), FakeRestClient())  # type: ignore[arg-type]

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                MCP_PATH,
                headers=headers("tools/call", "list_pets"),
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "_meta": meta(),
                        "name": "list_pets",
                        "arguments": {"species": "龙"},
                    },
                },
            )

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["isError"] is True
    assert result["structuredContent"]["error"]["code"] == "VALIDATION_ERROR"


def test_app_uses_mock_transport_not_real_go_service() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 200,
                "message": "ok",
                "data": {
                    "items": [],
                    "total": 0,
                    "page": 1,
                    "pageSize": 20,
                    "totalPages": 0,
                    "totalCost": 0,
                },
            },
        )

    rest_client = PetHospitalRestClient(settings(), transport=httpx.MockTransport(handler))
    assert rest_client.base_url == "http://backend.test"
