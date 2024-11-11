import aiohttp

from typing import Any, Optional


async def async_get(url: str, headers: Optional[Any] = None) -> str:
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url=url) as response:
            response.raise_for_status()
            return await response.text()


async def async_post(
    url: str, json: dict[str, Any], headers: Optional[Any] = None
) -> str:
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url=url, json=json) as response:
            response.raise_for_status()
            return await response.text()


async def async_put(
    url: str, json: dict[str, Any], headers: Optional[Any] = None
) -> str:
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.put(url=url, json=json) as response:
            response.raise_for_status()
            return await response.text()


async def async_delete(url: str, headers: Optional[Any] = None) -> str:
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.delete(url=url) as response:
            response.raise_for_status()
            return await response.text()


__all__ = ["async_get", "async_post", "async_put", "async_delete"]
