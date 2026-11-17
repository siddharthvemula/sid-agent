import unittest

from sid_agent.store import Store


class TestStore(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")

    def tearDown(self):
        self.store.close()

    def test_task_lifecycle(self):
        t = self.store.create_task("Submit form", due="2026-11-20")
        self.assertEqual(t["status"], "open")
        tasks = self.store.list_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["title"], "Submit form")
        self.store.complete_task(t["id"])
        self.assertEqual(self.store.list_tasks(), [])
        self.assertEqual(len(self.store.list_tasks("done")), 1)

    def test_application_lifecycle(self):
        self.store.log_application("Acme", "SWE Intern")
        self.store.log_application("Globex", "ML Intern")
        apps = self.store.list_applications()
        self.assertEqual(len(apps), 2)
        res = self.store.update_application("acme", "interview")
        self.assertEqual(res["updated"], 1)
        apps = self.store.list_applications()
        self.assertEqual(apps[0]["status"], "interview")

    def test_memory_upsert(self):
        self.store.add_memory("gym", "UMD Eppley")
        self.store.add_memory("gym", "UMD Ritchie")
        self.assertEqual(self.store.recall_memory("gym")["value"], "UMD Ritchie")
        self.assertIsNone(self.store.recall_memory("nope")["value"])


if __name__ == "__main__":
    unittest.main()
