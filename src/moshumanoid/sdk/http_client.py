import asyncio
from typing import Any, Callable, Coroutine, List

import aiohttp

from .logger import Logger
from .message import Message
from .network_client import INetworkClient


class HttpClient(INetworkClient):
    """The HTTP client to communicate with the server."""

    _logger = Logger("HttpClient")

    def __init__(self, host: str, port: int, token: str):
        """Initializes a new instance of the HttpClient class.

        Args:
            host: The server address.
            port: The server port.
            token: The token of the client.
        """
        self._url: str = f"http://{host}:{port}/"
        self._token: str = token

        self._callback_list: List[Callable[[Message],
                                           Coroutine[Any, Any, None]]] = []
        self._task_list: List[asyncio.Task] = []

        self._session = aiohttp.ClientSession()

    async def connect(self) -> None:
        self._task_list.append(
            asyncio.create_task(self._loop())
        )

    async def disconnect(self) -> None:
        for task in self._task_list:
            task.cancel()

        await self._session.close()

    async def register_callback(self, callback: Callable[[Message], Coroutine[Any, Any, None]]) -> None:
        self._callback_list.append(callback)

    async def send(self, msg: Message) -> None:
        try:
            async with self._session.post(
                self._url,
                json=msg.to_dict(),
                headers={"Authorization": f"Bearer {self._token}"}
            ) as response:
                if response.status == 204:
                    return

                else:
                    raise Exception(
                        f"HTTP status: {response.status} {response.reason}"
                    )

        except Exception as e:
            self._logger.error(f"Failed to send: {e}")

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(0.1)

            try:
                async with self._session.get(
                    self._url,
                    headers={"Authorization": f"Bearer {self._token}"}
                ) as response:
                    if response.status == 204:
                        continue

                    elif response.status == 200:
                        msg = Message(await response.json())
                        for callback in self._callback_list:
                            await callback(msg)

                    else:
                        raise Exception(
                            f"HTTP status: {response.status} {response.reason}"
                        )

            except Exception as e:
                self._logger.error(f"Failed to receive: {e}")
                await asyncio.sleep(1)
                continue
