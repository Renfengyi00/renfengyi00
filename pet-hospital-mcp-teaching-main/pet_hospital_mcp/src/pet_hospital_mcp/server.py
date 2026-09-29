from __future__ import annotations

import json
import logging
import time
from typing import Any

from mcp.server.context import ServerRequestContext
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp_types import CallToolRequestParams, CallToolResult, TextContent
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from pet_hospital_mcp.config import Settings, load_settings
from pet_hospital_mcp.errors import ErrorCode, ToolFailure, error_result
from pet_hospital_mcp.logging_config import log_tool_call
from pet_hospital_mcp.rest_client import PetHospitalRestClient
from pet_hospital_mcp.tools.list_pets import (
    LIST_PETS_DESCRIPTION,
    ListPetsInput,
    parse_list_pets_input,
    registered_list_pets,
)

PROTOCOL_VERSION = "2026-07-28"
MCP_PATH = "/mcp"

logger = logging.getLogger("pet_hospital_mcp.server")


class PetHospitalMCPServer(MCPServer[Any]):
    def __init__(self, rest_client: PetHospitalRestClient, *args: Any, **kwargs: Any) -> None:
        self.rest_client = rest_client
        super().__init__(*args, **kwargs)

    async def _handle_call_tool(
        self, ctx: ServerRequestContext[Any, Any], params: CallToolRequestParams
    ) -> CallToolResult:
        if params.name != "list_pets":
            return error_result(
                ErrorCode.VALIDATION_ERROR,
                "Unknown tool.",
                {"tool_name": params.name},
            )

        raw_args = params.arguments or {}
        start = time.perf_counter()
        try:
            parsed = parse_list_pets_input(raw_args)
            result = await self.rest_client.list_pets(parsed)
            payload = result.model_dump(mode="json")
            log_tool_call(
                logger,
                tool_name="list_pets",
                params=raw_args,
                status="success",
                duration_ms=(time.perf_counter() - start) * 1000,
            )
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                    )
                ],
                structured_content=payload,
                is_error=False,
            )
        except ToolFailure as exc:
            log_tool_call(
                logger,
                tool_name="list_pets",
                params=raw_args,
                status=exc.envelope.error.code.value,
                duration_ms=(time.perf_counter() - start) * 1000,
            )
            return error_result(
                exc.envelope.error.code,
                exc.envelope.error.message,
                exc.envelope.error.details,
            )
        except Exception:
            logger.exception("unhandled list_pets failure")
            log_tool_call(
                logger,
                tool_name="list_pets",
                params=raw_args,
                status=ErrorCode.INTERNAL_ERROR.value,
                duration_ms=(time.perf_counter() - start) * 1000,
            )
            return error_result(
                ErrorCode.INTERNAL_ERROR,
                "The MCP server failed while processing list_pets.",
                {},
            )


def create_server(settings: Settings | None = None, rest_client: PetHospitalRestClient | None = None) -> PetHospitalMCPServer:
    settings = settings or load_settings()
    rest_client = rest_client or PetHospitalRestClient(settings)
    server = PetHospitalMCPServer(
        rest_client,
        name="pet-hospital-mcp",
        title="Pet Hospital MCP",
        description="MCP 2026-07-28 wrapper for the Go Pet Hospital REST API.",
        version="0.1.0",
    )
    server.add_tool(
        registered_list_pets,
        name="list_pets",
        title="List pet records",
        description=LIST_PETS_DESCRIPTION,
        structured_output=True,
    )
    tool = server._tool_manager.get_tool("list_pets")
    if tool is not None:
        tool.parameters = ListPetsInput.model_json_schema()

    @server.custom_route("/health", methods=["GET"])
    async def health(_: Request) -> Response:
        return JSONResponse(
            {
                "status": "ok",
                "service": "pet-hospital-mcp",
                "protocolVersion": PROTOCOL_VERSION,
                "mcpPath": MCP_PATH,
                "backend": settings.pet_hospital_base_url,
            }
        )

    return server


def create_app(settings: Settings | None = None, rest_client: PetHospitalRestClient | None = None) -> Starlette:
    settings = settings or load_settings()
    server = create_server(settings, rest_client)
    return server.streamable_http_app(
        streamable_http_path=MCP_PATH,
        json_response=True,
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        host=settings.host,
    )
