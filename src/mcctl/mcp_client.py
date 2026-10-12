"""麦当劳 MCP 真实客户端（Streamable HTTP + 官方 Python SDK）。

接入地址 https://mcp.mcd.cn ，请求头携带 ``Authorization: Bearer <Token>``。
协议流程：initialize → notifications/initialized → tools/list · tools/call。

仅当配置了有效 MCP Token 时启用；未安装 ``mcp`` 包或无法连通时，
``service.get_server`` 会自动降级到离线演示模式并给出提示。
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any

from mcctl.mock_client import McdServer

# 连接 / 鉴权类失败时给用户的统一提示
CONN_HINT = (
    "无法连接麦当劳官方 MCP（https://mcp.mcd.cn）。请检查：网络是否可达、"
    "MCD_MCP_TOKEN 是否有效（无效会返回 401）、是否触发限流（429，600 次/分钟）。"
    "你也可以去掉 --live、使用离线演示模式（--mock）先体验完整流程。"
)
NO_SDK_HINT = "真实连接需要官方 MCP SDK，请先安装：pip install \"mcctl[mcp]\"（或 pip install \"mcp>=1.2\"）。"


class RealMCPClient(McdServer):
    """通过官方 MCP SDK 连接麦当劳远程 MCP Server。"""

    mode = "live"

    def __init__(self, url: str, token: str, timeout: float = 30.0) -> None:
        self.url = url
        self.token = token
        self.timeout = timeout
        self._tools_cache: list[str] | None = None

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json, text/event-stream",
        }

    @asynccontextmanager
    async def _connect(self):
        """在同一协程内完成连接的建立与关闭，避免 SDK task group 跨 task 退出。"""
        try:
            from mcp import ClientSession
            from mcp.client.streamable_http import streamablehttp_client
        except ImportError as exc:
            raise RuntimeError(NO_SDK_HINT) from exc

        async with streamablehttp_client(
            self.url, headers=self._headers(), timeout=self.timeout
        ) as (read, write, _get_sid):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session

    @staticmethod
    def _parse(result: Any) -> Any:
        """把 CallToolResult 归一化为 Python 对象。"""
        # 工具显式声明的结构化输出优先
        structured = getattr(result, "structuredContent", None)
        if structured:
            return {"ok": True, "source": "live", "data": structured}
        texts: list[str] = []
        for block in getattr(result, "content", []) or []:
            btype = getattr(block, "type", "")
            if btype == "text":
                texts.append(getattr(block, "text", ""))
            elif btype == "resource" and hasattr(block, "resource"):
                texts.append(getattr(block.resource, "text", "") or "")
        raw = "\n".join(t for t in texts if t).strip()
        if not raw:
            return {"ok": True, "source": "live", "data": None}
        try:
            parsed = json.loads(raw)
            return {"ok": True, "source": "live", "data": parsed}
        except json.JSONDecodeError:
            # 兼容直接返回纯文本的工具
            return {"ok": True, "source": "live", "data": {"text": raw}}

    async def health_check(self) -> bool:
        """探测连通性（auto 模式据此决定是否降级）。"""
        try:
            async with self._connect() as session:
                await session.list_tools()
            return True
        except Exception:
            return False

    async def tools(self) -> list[str]:
        if self._tools_cache is not None:
            return self._tools_cache
        try:
            async with self._connect() as session:
                res = await session.list_tools()
                self._tools_cache = [t.name for t in res.tools]
            return self._tools_cache
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(CONN_HINT) from exc

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        try:
            async with self._connect() as session:
                result = await session.call_tool(name, arguments or {})
                if getattr(result, "isError", False):
                    return {"ok": False, "error": f"工具 {name} 返回错误", "detail": self._parse(result)}
                return self._parse(result)
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(CONN_HINT) from exc
