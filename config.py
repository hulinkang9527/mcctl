"""运行配置：MCP Token、接入地址与连接模式。

配置优先级：函数参数 > 环境变量 > 项目根目录 .env 文件 > 默认值。
真实 Token 只会从本地环境读取，绝不硬编码、绝不随仓库分发。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

DEFAULT_MCP_URL = "https://mcp.mcd.cn"


class Mode(str, Enum):
    """连接模式。"""

    AUTO = "auto"   # 有 Token 且可用则真实，否则自动降级离线演示
    LIVE = "live"   # 强制连接官方 MCP
    MOCK = "mock"   # 强制离线演示（内置仿真数据）


def _load_dotenv(start: Path | None = None) -> None:
    """极简 .env 加载器（无第三方依赖），只在变量未设置时填充。"""
    cur = (start or Path.cwd()).resolve()
    for base in (cur, *cur.parents):
        envf = base / ".env"
        if envf.is_file():
            try:
                for line in envf.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
            except OSError:
                pass
            return


@dataclass
class Settings:
    token: str | None
    url: str
    mode: Mode

    @property
    def is_mock(self) -> bool:
        if self.mode is Mode.MOCK:
            return True
        if self.mode is Mode.LIVE:
            return False
        # auto：没有 Token 就离线演示
        return not bool(self.token)

    @classmethod
    def load(
        cls,
        *,
        token: str | None = None,
        url: str | None = None,
        mode: str | Mode | None = None,
        load_env: bool = True,
    ) -> "Settings":
        if load_env:
            _load_dotenv()
        tok = token or os.environ.get("MCD_MCP_TOKEN") or None
        if tok and tok.strip().lower() in {"", "your_mcp_token_here", "none"}:
            tok = None
        base_url = (
            url
            or os.environ.get("MCD_MCP_URL")
            or DEFAULT_MCP_URL
        )
        m = mode or os.environ.get("MCCTL_MODE") or Mode.AUTO.value
        if isinstance(m, str):
            m = Mode(m.lower())
        return Settings(token=tok, url=base_url.rstrip("/"), mode=m)  # type: ignore[arg-type]
