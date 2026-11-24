import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from neurodaily.config import DEFAULT_CONFIG


@unittest.skipUnless(importlib.util.find_spec("mcp"), "Optional MCP SDK unavailable")
class OptimizationMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_local_stdio_exposes_only_read_operations(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        with TemporaryDirectory() as directory:
            path = Path(directory) / "test-profile.json"
            config = DEFAULT_CONFIG()
            config.profile = "mcp-integration-test"
            config.save(str(path))
            params = StdioServerParameters(command=sys.executable, env={"NEURODAILY_HOME": directory},
                                         args=["-m", "neurodaily", "--config", str(path), "mcp"])
            async with stdio_client(params) as (reader, writer):
                async with ClientSession(reader, writer) as client:
                    await client.initialize()
                    response = await client.list_tools()
                    self.assertEqual({tool.name for tool in response.tools}, {
                        "search_history", "search_source_health", "search_rule_attribution",
                        "search_optimization_review",
                    })
                    self.assertTrue(all(tool.annotations.readOnlyHint for tool in response.tools))
                    result = await client.call_tool("search_history", {"limit": 1})
                    self.assertFalse(result.isError)
                    self.assertEqual(result.structuredContent, {"result": []})
