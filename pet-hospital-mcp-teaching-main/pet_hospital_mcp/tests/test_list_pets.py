from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from pet_hospital_mcp.config import Settings
from pet_hospital_mcp.errors import ErrorCode, ToolFailure
from pet_hospital_mcp.rest_client import PetHospitalRestClient
from pet_hospital_mcp.tools.list_pets import parse_list_pets_input


def settings() -> Settings:
    return Settings(
        pet_hospital_base_url="http://backend.test",
        request_timeout_seconds=0.1,
        backend_retries=1,
    )


def go_success(data: dict[str, Any]) -> httpx.Response:
    return httpx.Response(200, json={"code": 200, "message": "ok", "data": data})


def list_data() -> dict[str, Any]:
    return {
        "items": [
            {
                "id": "PET-000001",
                "name": "旺财",
                "species": "犬",
                "ownerName": "张三",
                "ownerPhone": "13800001111",
                "doctor": "李医生",
                "disease": "急性肠胃炎",
                "status": "待就诊",
                "records": None,
                "charges": [],
                "totalCost": 0,
                "visitCount": 0,
                "createdAt": "2026-01-01T00:00:00+08:00",
                "updatedAt": "2026-01-01T00:00:00+08:00",
            }
        ],
        "total": 1,
        "page": 1,
        "pageSize": 10,
        "totalPages": 1,
        "totalCost": 0,
    }


@pytest.mark.asyncio
async def test_list_pets_forwards_supported_query_params() -> None:
    seen: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return go_success(list_data())

    client = PetHospitalRestClient(settings(), transport=httpx.MockTransport(handler))
    params = parse_list_pets_input(
        {
            "q": "肠胃炎",
            "name": "旺财",
            "ownerName": "张三",
            "ownerPhone": "138",
            "species": "犬",
            "doctor": "李医生",
            "disease": "肠胃炎",
            "status": "待就诊",
            "min": 1,
            "max": 2000,
            "sortBy": "totalCost",
            "order": "desc",
            "page": 1,
            "pageSize": 10,
        }
    )

    result = await client.list_pets(params)

    assert result.total == 1
    assert seen[0].url.path == "/api/v1/pets"
    query = dict(seen[0].url.params)
    assert query == {
        "q": "肠胃炎",
        "name": "旺财",
        "ownerName": "张三",
        "ownerPhone": "138",
        "species": "犬",
        "doctor": "李医生",
        "disease": "肠胃炎",
        "status": "待就诊",
        "min": "1.0",
        "max": "2000.0",
        "sortBy": "totalCost",
        "order": "desc",
        "page": "1",
        "pageSize": "10",
    }
    await client.aclose()


@pytest.mark.parametrize(
    "arguments",
    [
        {"species": "龙"},
        {"status": "已结束"},
        {"sortBy": "privateField"},
        {"order": "descending"},
        {"page": 0},
        {"pageSize": 501},
        {"min": -1},
        {"min": 9, "max": 3},
        {"ownerPhone": 13800001111},
        {"unknown": "nope"},
        {"min": float("nan")},
        {"max": float("inf")},
    ],
)
def test_input_validation_failure(arguments: dict[str, Any]) -> None:
    with pytest.raises(ToolFailure) as exc:
        parse_list_pets_input(arguments)
    assert exc.value.envelope.error.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [400, 500])
async def test_backend_4xx_5xx_maps_to_api_error(status_code: int) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"code": status_code, "message": "bad"})

    client = PetHospitalRestClient(settings(), transport=httpx.MockTransport(handler))

    with pytest.raises(ToolFailure) as exc:
        await client.list_pets(parse_list_pets_input({}))
    assert exc.value.envelope.error.code == ErrorCode.BACKEND_API_ERROR
    assert exc.value.envelope.error.details["http_status"] == status_code
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raised,expected",
    [
        (httpx.ReadTimeout("slow"), ErrorCode.BACKEND_TIMEOUT),
        (httpx.ConnectError("offline"), ErrorCode.BACKEND_UNAVAILABLE),
    ],
)
async def test_timeout_and_connection_errors(raised: Exception, expected: ErrorCode) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        raise raised

    client = PetHospitalRestClient(settings(), transport=httpx.MockTransport(handler))

    with pytest.raises(ToolFailure) as exc:
        await client.list_pets(parse_list_pets_input({}))
    assert exc.value.envelope.error.code == expected
    await client.aclose()


@pytest.mark.asyncio
async def test_backend_invalid_json() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json")

    client = PetHospitalRestClient(settings(), transport=httpx.MockTransport(handler))

    with pytest.raises(ToolFailure) as exc:
        await client.list_pets(parse_list_pets_input({}))
    assert exc.value.envelope.error.code == ErrorCode.BACKEND_INVALID_RESPONSE
    await client.aclose()


@pytest.mark.asyncio
async def test_backend_invalid_data_model() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return go_success({"items": []})

    client = PetHospitalRestClient(settings(), transport=httpx.MockTransport(handler))

    with pytest.raises(ToolFailure) as exc:
        await client.list_pets(parse_list_pets_input({}))
    assert exc.value.envelope.error.code == ErrorCode.BACKEND_INVALID_RESPONSE
    await client.aclose()
