import unittest

from sid_agent.agent import Agent
from sid_agent.store import Store
from sid_agent.tools import parse_prereqs


class TestParsePrereqs(unittest.TestCase):
    def test_extracts_codes_in_order(self):
        text = "Minimum grade of C- in CMSC132; and minimum grade of C- in MATH141."
        self.assertEqual(parse_prereqs(text), ["CMSC132", "MATH141"])

    def test_handles_none_and_duplicates(self):
        self.assertEqual(parse_prereqs(None), [])
        self.assertEqual(parse_prereqs("CMSC250 and CMSC250 again"), ["CMSC250"])


class TestAgentMock(unittest.TestCase):
    def setUp(self):
        self.agent = Agent(store=Store(":memory:"))

    def test_create_task_via_agent(self):
        out = self.agent.handle("remind me to submit the Freddie Mac thank-you by 2026-11-20")
        self.assertIn("task #1", out)
        tasks = self.agent.store.list_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["due"], "2026-11-20")

    def test_log_application_via_agent(self):
        out = self.agent.handle("log application to Acme for SWE Intern")
        self.assertIn("Acme", out)
        apps = self.agent.store.list_applications()
        self.assertEqual(apps[0]["company"], "Acme")

    def test_profile_courses_via_agent(self):
        out = self.agent.handle("what courses am I taking?")
        self.assertIn("CMSC132", out)

    def test_memory_roundtrip_via_agent(self):
        self.agent.handle("remember that gym is UMD Eppley")
        out = self.agent.handle("what is my gym?")
        self.assertIn("UMD Eppley", out)

    def test_unknown_request_is_honest(self):
        out = self.agent.handle("book me a flight to Madison")
        self.assertIn("can't do that yet", out)


if __name__ == "__main__":
    unittest.main()
