import unittest

from sid_agent import tools as tools_mod
from sid_agent.providers import ClaudeProvider, OpenAIProvider, to_json_schema


class FakeTransport:
    """Captures the request and returns a canned response."""

    def __init__(self, response):
        self.response = response
        self.calls = []

    def __call__(self, url, headers, payload):
        self.calls.append({"url": url, "headers": headers, "payload": payload})
        return self.response


class TestSchemaConversion(unittest.TestCase):
    def test_types(self):
        schema = to_json_schema({"title": "string", "due": "string|null", "task_id": "integer"})
        props = schema["properties"]
        self.assertEqual(props["title"], {"type": "string"})
        self.assertEqual(props["due"], {"type": ["string", "null"]})
        self.assertEqual(props["task_id"], {"type": "integer"})


class TestClaudeProvider(unittest.TestCase):
    def test_plan_parses_tool_use(self):
        transport = FakeTransport({
            "content": [
                {"type": "tool_use", "name": "create_task",
                 "input": {"title": "submit the form", "due": "2026-11-20"}}
            ]
        })
        provider = ClaudeProvider(api_key="test-key", http_post=transport)
        plan = provider.plan("remind me to submit the form", tools_mod.REGISTRY)
        self.assertEqual(len(plan.tool_calls), 1)
        self.assertEqual(plan.tool_calls[0].name, "create_task")
        self.assertEqual(plan.tool_calls[0].arguments["due"], "2026-11-20")
        sent = transport.calls[0]
        self.assertEqual(sent["headers"]["x-api-key"], "test-key")
        tool_names = [t["name"] for t in sent["payload"]["tools"]]
        self.assertIn("create_task", tool_names)

    def test_plan_text_only(self):
        transport = FakeTransport({"content": [{"type": "text", "text": "Hello Sid."}]})
        provider = ClaudeProvider(api_key="k", http_post=transport)
        plan = provider.plan("hi", tools_mod.REGISTRY)
        self.assertEqual(plan.tool_calls, [])
        self.assertEqual(plan.text, "Hello Sid.")

    def test_compose_returns_text(self):
        transport = FakeTransport({"content": [{"type": "text", "text": "Done - task created."}]})
        provider = ClaudeProvider(api_key="k", http_post=transport)
        out = provider.compose("remind me", [{"tool": "create_task", "result": {"id": 1}}])
        self.assertEqual(out, "Done - task created.")

    def test_missing_key_raises(self):
        provider = ClaudeProvider(api_key=None, http_post=FakeTransport({}))
        provider.api_key = None
        with self.assertRaises(RuntimeError):
            provider.plan("hi", tools_mod.REGISTRY)


class TestOpenAIProvider(unittest.TestCase):
    def test_plan_parses_function_call(self):
        transport = FakeTransport({
            "choices": [{
                "message": {
                    "content": None,
                    "tool_calls": [{
                        "function": {
                            "name": "log_application",
                            "arguments": '{"company": "Acme", "role": "SWE Intern"}',
                        }
                    }],
                }
            }]
        })
        provider = OpenAIProvider(api_key="k", http_post=transport)
        plan = provider.plan("log it", tools_mod.REGISTRY)
        self.assertEqual(plan.tool_calls[0].name, "log_application")
        self.assertEqual(plan.tool_calls[0].arguments["company"], "Acme")
        sent = transport.calls[0]
        self.assertEqual(sent["headers"]["Authorization"], "Bearer k")
        self.assertEqual(sent["payload"]["tools"][0]["type"], "function")


if __name__ == "__main__":
    unittest.main()
