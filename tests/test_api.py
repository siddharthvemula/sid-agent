import unittest

try:
    from fastapi.testclient import TestClient
    from sid_agent.api import create_app
    from sid_agent.providers import MockProvider
    from sid_agent.store import Store
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


@unittest.skipUnless(HAS_FASTAPI, "fastapi not installed (see requirements.txt)")
class TestApi(unittest.TestCase):
    def setUp(self):
        app = create_app(store=Store(":memory:"), provider=MockProvider())
        self.client = TestClient(app)

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["provider"], "mock")

    def test_chat_creates_task_and_lists_it(self):
        r = self.client.post("/chat", json={"message": "remind me to call the advisor by 2026-11-25"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("task #1", r.json()["reply"])
        tasks = self.client.get("/tasks").json()
        self.assertEqual(len(tasks["open"]), 1)
        self.assertEqual(tasks["open"][0]["due"], "2026-11-25")

    def test_profile_endpoint_is_public_layer(self):
        data = self.client.get("/profile").json()
        self.assertEqual(data["graduation"], "May 2028")
        self.assertNotIn("email", data)
        self.assertNotIn("phone", data)


if __name__ == "__main__":
    unittest.main()
