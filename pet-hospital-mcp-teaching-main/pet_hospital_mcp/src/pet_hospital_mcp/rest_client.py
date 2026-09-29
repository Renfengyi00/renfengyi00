from __future__ import annotations

from typing import Any

import httpx
from pydantic import ValidationError

from pet_hospital_mcp.config import Settings
from pet_hospital_mcp.errors import ErrorCode, ToolFailure
from pet_hospital_mcp.tools.list_pets import ListPetsInput, ListPetsOutput


class PetHospitalRestClient:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=settings.pet_hospital_base_url,
            timeout=settings.request_timeout_seconds,
            transport=transport,
        )

    @property
    def base_url(self) -> str:
        return self.settings.pet_hospital_base_url

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def list_pets(self, params: ListPetsInput) -> ListPetsOutput:
        response = await self._get_with_retries("/api/v1/pets", params.query_params())
        return self._parse_list_response(response)

    async def _get_with_retries(self, path: str, params: dict[str, str]) -> httpx.Response:
        last_exc: Exception | None = None
        attempts = self.settings.backend_retries + 1
        for attempt in range(attempts):
            try:
                response = await self._client.get(path, params=params)
                if response.status_code >= 500 and attempt < attempts - 1:
                    continue
                return response
            except httpx.TimeoutException as exc:
                last_exc = exc
                if attempt >= attempts - 1:
                    raise ToolFailure(
                        ErrorCode.BACKEND_TIMEOUT,
                        "The Go pet hospital API timed out.",
                        {"attempts": attempts},
                    ) from exc
            except httpx.TransportError as exc:
                last_exc = exc
                if attempt >= attempts - 1:
                    raise ToolFailure(
                        ErrorCode.BACKEND_UNAVAILABLE,
                        "The Go pet hospital API is unavailable.",
                        {"attempts": attempts},
                    ) from exc
        raise ToolFailure(
            ErrorCode.BACKEND_UNAVAILABLE,
            "The Go pet hospital API is unavailable.",
            {"attempts": attempts, "cause": type(last_exc).__name__ if last_exc else "unknown"},
        )

    def _parse_list_response(self, response: httpx.Response) -> ListPetsOutput:
        if response.status_code >= 400:
            raise ToolFailure(
                ErrorCode.BACKEND_API_ERROR,
                "The Go pet hospital API returned an error response.",
                {"http_status": response.status_code},
            )

        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise ToolFailure(
                ErrorCode.BACKEND_INVALID_RESPONSE,
                "The Go pet hospital API returned invalid JSON.",
                {"http_status": response.status_code},
            ) from exc

        if not isinstance(payload, dict):
            raise ToolFailure(
                ErrorCode.BACKEND_INVALID_RESPONSE,
                "The Go pet hospital API response is not an object.",
                {},
            )

        if payload.get("code") != 200:
            raise ToolFailure(
                ErrorCode.BACKEND_API_ERROR,
                "The Go pet hospital API reported an application error.",
                {"backend_code": payload.get("code"), "backend_message": payload.get("message")},
            )

        try:
            return ListPetsOutput.model_validate(payload.get("data"))
        except ValidationError as exc:
            raise ToolFailure(
                ErrorCode.BACKEND_INVALID_RESPONSE,
                "The Go pet hospital API data shape is invalid.",
                {"field_count": len(exc.errors())},
            ) from exc
