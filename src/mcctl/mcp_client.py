"""麦当劳 MCP 真实客户端（Streamable HTTP + 官方 Python SDK）。

接入地址 https://mcp.mcd.cn ，请求头携带 ``Authorization: Bearer <Token>``。
协议流程：initialize → notifications/initialized → tools/list · tools/call。

仅当配置了有效 MCP Token 时启用；未安装 ``mcp`` 包或无法连通时，
``service.get_server`` 会自动降级到离线演示模式并给出提示。
"""
from __future__ import annotations

import json
from contextlib import AsyncExitStack, suppress
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
        self._stack: AsyncExitStack | None = None
        self._session: Any = None

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json, text/event-stream",
        }

    @staticmethod
    def _connect_factory() -> tuple[Any, bool]:
        """探测当前 mcp SDK 的 Streamable HTTP 连接 API。

        mcp SDK 近年多次改动连接入口，这里做三档兼容：
        - 旧版（mcp<1.10）：``streamablehttp_client(url, headers=..., timeout=...)``
        - 新版（mcp 1.10+）：改名 ``streamable_http_client``，鉴权头与超时改由
          ``http_client``（httpx / httpx2 的 AsyncClient）传入；
        - mcp 2.x：同上新名，但底层依赖 ``httpx2``。

        返回 ``(factory, modern)``：``modern=False`` 表示走旧版直传参数签名，
        ``modern=True`` 表示需先构造 http_client 再传入。
        """
        try:
            from mcp.client.streamable_http import streamable_http_client as factory
        except ImportError:
            try:
                from mcp.client.streamable_http import streamablehttp_client as factory
            except ImportError as exc:
                raise RuntimeError(NO_SDK_HINT) from exc
            return factory, False
        return factory, True

    @staticmethod
    def _new_http_client(headers: dict[str, str], timeout: float) -> Any:
        """构造新版 SDK 需要的 http_client（mcp 2.x 用 httpx2，1.10+ 用 httpx）。"""
        try:
            import httpx2
            return httpx2.AsyncClient(headers=headers, timeout=timeout)
        except ImportError:
            import httpx
            return httpx.AsyncClient(headers=headers, timeout=timeout)

    async def _get_session(self) -> Any:
        """懒建立并复用同一个 MCP 会话（HTTP 建连 + initialize 只发生一次）。

        旧实现每次 tools/call 都重新建连并 initialize，派对策划这类需要几十次
        调用的命令会产生几十次握手；这里在 client 生命周期内复用一个
        ClientSession，由 :meth:`aclose` 在命令结束时、同一 event loop 内显式关闭。
        """
        if self._session is not None:
            return self._session
        try:
            from mcp import ClientSession
        except ImportError as exc:
            raise RuntimeError(NO_SDK_HINT) from exc

        factory, modern = self._connect_factory()
        stack = AsyncExitStack()
        await stack.__aenter__()
        try:
            if modern:
                http_client = self._new_http_client(self._headers(), self.timeout)
                await stack.enter_async_context(http_client)
                # 新版 SDK（mcp 1.10+ / 2.x）context 只返回 (read, write)；
                # 旧版返回 (read, write, get_session_id)，由 else 分支处理。
                read, write = await stack.enter_async_context(
                    factory(self.url, http_client=http_client)
                )
            else:
                read, write, _get_sid = await stack.enter_async_context(
                    factory(self.url, headers=self._headers(), timeout=self.timeout)
                )
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
        except Exception:
            await stack.aclose()
            raise
        self._stack, self._session = stack, session
        return session

    async def aclose(self) -> None:
        """关闭并清理复用的会话（必须在持有它的 event loop 内调用）。"""
        if self._stack is not None:
            with suppress(Exception):
                await self._stack.aclose()
            self._stack = None
            self._session = None

    @staticmethod
    def _extract_json(text: str) -> Any | None:
        """从「说明文字 + 完整 JSON」的文本里把 JSON 抠出来。

        真实模式实测：官方有时直接把 API 响应包成一段 Markdown 说明
        （``# API Response Information`` + 字段释义 + 完整 JSON），此时
        ``json.loads`` 整段会失败，必须再定位 JSON 片段，否则解析层只能拿到
        一段文本、所有列表都变空。优先取**末尾**的 JSON（说明里也可能出现花括号）。
        """
        stripped = text.strip()
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
        lines = stripped.splitlines()
        for i in range(len(lines) - 1, -1, -1):
            head = lines[i].lstrip()
            if head.startswith("{") or head.startswith("["):
                try:
                    return json.loads("\n".join(lines[i:]).strip())
                except json.JSONDecodeError:
                    continue
        # 兜底：全文扫描第一个可完整闭合的 JSON 片段
        for start, ch in enumerate(stripped):
            if ch not in "{[":
                continue
            close = "}" if ch == "{" else "]"
            depth, in_str, esc = 0, False, False
            for i in range(start, len(stripped)):
                c = stripped[i]
                if in_str:
                    if esc:
                        esc = False
                    elif c == "\\":
                        esc = True
                    elif c == '"':
                        in_str = False
                    continue
                if c == '"':
                    in_str = True
                elif c == ch:
                    depth += 1
                elif c == close:
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(stripped[start:i + 1])
                        except json.JSONDecodeError:
                            break
        return None

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
        parsed = RealMCPClient._extract_json(raw)
        if parsed is not None:
            return {"ok": True, "source": "live", "data": parsed}
        # 兼容直接返回纯文本的工具（如 list-nutrition-foods 的表格文本）
        return {"ok": True, "source": "live", "data": {"text": raw}}

    async def health_check(self) -> bool:
        """探测连通性并建立/复用会话（auto 模式据此决定是否降级）。"""
        try:
            session = await self._get_session()
            await session.list_tools()
            return True
        except Exception:
            return False

    async def tools(self) -> list[str]:
        if self._tools_cache is not None:
            return self._tools_cache
        try:
            session = await self._get_session()
            res = await session.list_tools()
            self._tools_cache = [t.name for t in res.tools]
            return self._tools_cache
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(CONN_HINT) from exc

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        try:
            session = await self._get_session()
            result = await session.call_tool(name, arguments or {})
            if getattr(result, "isError", False):
                return {"ok": False, "error": f"工具 {name} 返回错误", "detail": self._parse(result)}
            return self._parse(result)
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(CONN_HINT) from exc
