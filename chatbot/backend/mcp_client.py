import asyncio
import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger("mcp")


class MCPServer:
    def __init__(self, name: str, command: str, args: list[str] = None,
                 env: dict[str, str] = None, cwd: str = None):
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.cwd = cwd
        self.process: Optional[asyncio.subprocess.Process] = None
        self.tools: list[dict] = []
        self._connected = False
        self._req_id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self) -> list[dict]:
        merged_env = {**os.environ, **self.env}
        self.process = await asyncio.create_subprocess_exec(
            self.command, *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=merged_env,
            cwd=self.cwd,
        )
        self._reader_task = asyncio.create_task(self._read_loop())

        result = await self._rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "opencode-chatbot", "version": "1.0.0"},
        })
        logger.info(f"MCP [{self.name}] initialized: {result}")

        await self._send_notification("notifications/initialized", {})

        tools_result = await self._rpc("tools/list", {})
        self.tools = tools_result.get("tools", [])
        self._connected = True
        logger.info(f"MCP [{self.name}] tools: {[t['name'] for t in self.tools]}")
        return self.tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if not self._connected:
            raise RuntimeError(f"MCP server '{self.name}' not connected")
        result = await self._rpc("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })
        return result

    async def _rpc(self, method: str, params: dict) -> dict:
        self._req_id += 1
        rid = self._req_id
        msg = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params}
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[rid] = future

        payload = json.dumps(msg, ensure_ascii=False) + "\n"
        self.process.stdin.write(payload.encode())
        await self.process.stdin.drain()

        try:
            result = await asyncio.wait_for(future, timeout=30)
        except asyncio.TimeoutError:
            self._pending.pop(rid, None)
            raise RuntimeError(f"MCP RPC timeout: {method}")
        return result

    async def _send_notification(self, method: str, params: dict):
        msg = {"jsonrpc": "2.0", "method": method, "params": params}
        payload = json.dumps(msg, ensure_ascii=False) + "\n"
        self.process.stdin.write(payload.encode())
        await self.process.stdin.drain()

    async def _read_loop(self):
        try:
            while self.process and self.process.stdout and not self.process.stdout.at_eof():
                line = await self.process.stdout.readline()
                if not line:
                    break
                try:
                    data = json.loads(line.decode())
                except json.JSONDecodeError:
                    continue
                rid = data.get("id")
                if rid is not None and rid in self._pending:
                    future = self._pending.pop(rid)
                    if "error" in data:
                        future.set_exception(RuntimeError(data["error"].get("message", "MCP error")))
                    else:
                        future.set_result(data.get("result", {}))
                # notifications/responses without id are ignored here
        except Exception as e:
            logger.error(f"MCP [{self.name}] reader error: {e}")
        finally:
            self._connected = False

    async def close(self):
        self._connected = False
        if self._reader_task:
            self._reader_task.cancel()
            self._reader_task = None
        if self.process:
            try:
                self.process.stdin.close()
            except Exception:
                pass
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except Exception:
                self.process.kill()
            self.process = None


class MCPManager:
    def __init__(self):
        self.servers: dict[str, MCPServer] = {}

    async def connect_server(self, config: dict) -> list[dict]:
        name = config["name"]
        if name in self.servers:
            await self.servers[name].close()
        server = MCPServer(
            name=name,
            command=config["command"],
            args=config.get("args", []),
            env=config.get("env"),
            cwd=config.get("cwd"),
        )
        tools = await server.connect()
        self.servers[name] = server
        return tools

    def get_all_tools(self) -> list[dict]:
        tools = []
        for server in self.servers.values():
            if server.connected:
                for t in server.tools:
                    tools.append({
                        "type": "function",
                        "function": {
                            "name": t["name"],
                            "description": t.get("description", ""),
                            "parameters": t.get("inputSchema", {"type": "object", "properties": {}}),
                        },
                    })
        return tools

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        for server in self.servers.values():
            if server.connected:
                for t in server.tools:
                    if t["name"] == tool_name:
                        return await server.call_tool(tool_name, arguments)
        raise RuntimeError(f"Tool '{tool_name}' not found on any MCP server")

    def status(self) -> list[dict]:
        return [
            {"name": s.name, "connected": s.connected, "tools": len(s.tools)}
            for s in self.servers.values()
        ]

    async def close_all(self):
        for server in self.servers.values():
            await server.close()
        self.servers.clear()


mcp_manager = MCPManager()
