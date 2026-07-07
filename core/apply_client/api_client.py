"""HTTP client for Yarba apply automation APIs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import aiohttp

from core.schemas.application_schemas import ApplicationProfile


class YarbaApplyApiError(Exception):
    """Raised when the Yarba API returns an error response."""


class YarbaApplyClient:
    """Thin async client for PAT-authenticated apply endpoints."""

    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._headers = {"Authorization": f"Bearer {token}"}

    async def prepare(
        self,
        *,
        job_url: str,
        job_description: str | None = None,
        compile_pdf: bool = True,
        generate_cover_letter: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "job_url": job_url,
            "compile_pdf": compile_pdf,
            "generate_cover_letter": generate_cover_letter,
        }
        if job_description is not None:
            payload["job_description"] = job_description
        return await self._request("POST", "/applications/prepare", json=payload)

    async def update_application(
        self,
        application_id: str,
        *,
        status: str,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"status": status}
        if error_message is not None:
            payload["error_message"] = error_message
        return await self._request(
            "PATCH", f"/applications/{application_id}", json=payload
        )

    async def download_resume_pdf(self, resume_id: str, destination: Path) -> Path:
        url = f"{self.base_url}/resumes/{resume_id}/pdf/download"
        async with aiohttp.ClientSession(headers=self._headers) as session:
            async with session.get(url) as response:
                if response.status >= 400:
                    detail = await response.text()
                    raise YarbaApplyApiError(
                        f"PDF download failed ({response.status}): {detail}"
                    )
                destination.write_bytes(await response.read())
        return destination

    @staticmethod
    def parse_application_profile(payload: dict[str, Any]) -> ApplicationProfile:
        return ApplicationProfile.model_validate(payload["application_profile"])

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with aiohttp.ClientSession(headers=self._headers) as session:
            async with session.request(method, url, json=json) as response:
                body = await self._read_body(response)
                if response.status >= 400:
                    raise YarbaApplyApiError(
                        f"{method} {path} failed ({response.status}): {body}"
                    )
                if isinstance(body, dict):
                    return body
                return {"data": body}

    @staticmethod
    async def _read_body(response: aiohttp.ClientResponse) -> Any:
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return await response.json()
        text = await response.text()
        return text or None
