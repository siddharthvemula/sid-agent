import unittest
from datetime import date, timedelta

from sid_agent import tools as tools_mod
from sid_agent.agent import Agent
from sid_agent.profile import Profile
from sid_agent.store import Store


def _ctx(store):
    return {"store": store, "profile": Profile.load()}


class TestDueSummary(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        today = date.today()
        self.store.create_task("overdue task", due=(today - timedelta(days=1)).isoformat())
        self.store.create_task("soon task", due=(today + timedelta(days=2)).isoformat())
        self.store.create_task("later task", due=(today + timedelta(days=30)).isoformat())
        self.store.create_task("undated task")

    def tearDown(self):
        self.store.close()

    def test_buckets(self):
        result = tools_mod.call_tool(_ctx(self.store), "due_summary", {})
        titles = {k: [t["title"] for t in result[k]] for k in
                  ("overdue", "due_soon", "later", "no_date")}
        self.assertEqual(titles["overdue"], ["overdue task"])
        self.assertEqual(titles["due_soon"], ["soon task"])
        self.assertEqual(titles["later"], ["later task"])
        self.assertEqual(titles["no_date"], ["undated task"])

    def test_agent_answers_whats_due(self):
        agent = Agent(store=self.store)
        out = agent.handle("what's due this week?")
        self.assertIn("overdue task", out)
        self.assertIn("Overdue", out)

    def test_agent_empty_plate(self):
        agent = Agent(store=Store(":memory:"))
        out = agent.handle("what do I have coming up?")
        self.assertIn("Nothing on your plate", out)


if __name__ == "__main__":
    unittest.main()
