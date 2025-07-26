#!/usr/bin/env python3
"""
MCP Compliance Test Script

This script tests the MCP compliance of all agents in the system.
Run this after starting all agents to verify they follow MCP standards.
"""

import asyncio
import httpx
import json
import sys
from typing import Dict, Any, List


class MCPComplianceTester:
    """Test MCP compliance of agents."""

    def __init__(self):
        self.agents = {
            "summarizer": "http://localhost:8001",
            "task_extractor": "http://localhost:8002",
        }
        self.results = {}

    async def test_discovery_endpoint(
        self, agent_name: str, base_url: str
    ) -> Dict[str, Any]:
        """Test the MCP discovery endpoint."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{base_url}/.well-known/mcp.json")
                response.raise_for_status()
                data = response.json()

                # Check MCP compliance
                issues = []

                # Check required fields
                if "tools" not in data:
                    issues.append("Missing 'tools' field")
                if "resources" not in data:
                    issues.append("Missing 'resources' field")
                if "capabilities" not in data:
                    issues.append("Missing 'capabilities' field")

                # Check tools structure
                if "tools" in data:
                    for i, tool in enumerate(data["tools"]):
                        if "name" not in tool:
                            issues.append(f"Tool {i}: Missing 'name' field")
                        if "description" not in tool:
                            issues.append(f"Tool {i}: Missing 'description' field")
                        if "inputSchema" not in tool:
                            issues.append(f"Tool {i}: Missing 'inputSchema' field")
                        elif not isinstance(tool["inputSchema"], dict):
                            issues.append(f"Tool {i}: 'inputSchema' must be an object")

                return {
                    "status": "PASS" if not issues else "FAIL",
                    "issues": issues,
                    "data": data,
                }

        except Exception as e:
            return {
                "status": "ERROR",
                "issues": [f"Request failed: {str(e)}"],
                "data": None,
            }

    async def test_invoke_endpoint(
        self, agent_name: str, base_url: str, tool_name: str
    ) -> Dict[str, Any]:
        """Test the MCP invoke endpoint."""
        try:
            # Test payload
            payload = {
                "name": tool_name,
                "arguments": {
                    "transcript": "This is a test transcript for MCP compliance testing. It contains enough content to meet the minimum length requirement."
                },
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{base_url}/invoke", json=payload)
                response.raise_for_status()
                data = response.json()

                # Check MCP compliance
                issues = []

                if "content" not in data:
                    issues.append("Missing 'content' field in response")
                elif not isinstance(data["content"], list):
                    issues.append("'content' field must be an array")
                elif len(data["content"]) == 0:
                    issues.append("'content' array is empty")
                else:
                    content_item = data["content"][0]
                    if "type" not in content_item:
                        issues.append("Content item missing 'type' field")
                    elif content_item["type"] != "text":
                        issues.append("Content type should be 'text'")
                    if "text" not in content_item:
                        issues.append("Content item missing 'text' field")

                return {
                    "status": "PASS" if not issues else "FAIL",
                    "issues": issues,
                    "data": data,
                }

        except Exception as e:
            return {
                "status": "ERROR",
                "issues": [f"Request failed: {str(e)}"],
                "data": None,
            }

    async def test_health_endpoint(
        self, agent_name: str, base_url: str
    ) -> Dict[str, Any]:
        """Test the health endpoint."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{base_url}/health")
                response.raise_for_status()
                data = response.json()

                return {"status": "PASS", "issues": [], "data": data}

        except Exception as e:
            return {
                "status": "ERROR",
                "issues": [f"Request failed: {str(e)}"],
                "data": None,
            }

    async def run_all_tests(self):
        """Run all MCP compliance tests."""
        print("🔍 Testing MCP Compliance...")
        print("=" * 50)

        for agent_name, base_url in self.agents.items():
            print(f"\n📋 Testing {agent_name.upper()} Agent ({base_url})")
            print("-" * 40)

            # Test discovery endpoint
            print("1. Testing discovery endpoint...")
            discovery_result = await self.test_discovery_endpoint(agent_name, base_url)
            print(f"   Status: {discovery_result['status']}")
            if discovery_result["issues"]:
                for issue in discovery_result["issues"]:
                    print(f"   ❌ {issue}")
            else:
                print("   ✅ Discovery endpoint is MCP compliant")

            # Test invoke endpoint for each tool
            if discovery_result["status"] == "PASS" and discovery_result["data"]:
                tools = discovery_result["data"].get("tools", [])
                for tool in tools:
                    tool_name = tool.get("name", "unknown")
                    print(f"2. Testing invoke endpoint for tool '{tool_name}'...")
                    invoke_result = await self.test_invoke_endpoint(
                        agent_name, base_url, tool_name
                    )
                    print(f"   Status: {invoke_result['status']}")
                    if invoke_result["issues"]:
                        for issue in invoke_result["issues"]:
                            print(f"   ❌ {issue}")
                    else:
                        print("   ✅ Invoke endpoint is MCP compliant")

            # Test health endpoint
            print("3. Testing health endpoint...")
            health_result = await self.test_health_endpoint(agent_name, base_url)
            print(f"   Status: {health_result['status']}")
            if health_result["issues"]:
                for issue in health_result["issues"]:
                    print(f"   ❌ {issue}")
            else:
                print("   ✅ Health endpoint is working")

            # Store results
            self.results[agent_name] = {
                "discovery": discovery_result,
                "invoke": invoke_result if "invoke_result" in locals() else None,
                "health": health_result,
            }

        # Summary
        print("\n" + "=" * 50)
        print("📊 MCP COMPLIANCE SUMMARY")
        print("=" * 50)

        all_passed = True
        for agent_name, results in self.results.items():
            print(f"\n{agent_name.upper()}:")
            for test_name, result in results.items():
                if result:
                    status_icon = "✅" if result["status"] == "PASS" else "❌"
                    print(f"  {status_icon} {test_name}: {result['status']}")
                    if result["status"] != "PASS":
                        all_passed = False

        if all_passed:
            print("\n🎉 ALL TESTS PASSED! Your agents are MCP compliant!")
        else:
            print("\n⚠️  Some tests failed. Please review the issues above.")

        return all_passed


async def main():
    """Main test function."""
    tester = MCPComplianceTester()

    try:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
