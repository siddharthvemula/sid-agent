import json
import os
import unittest

from sid_agent.profile import Profile

_PROFILE_JSON = os.path.join(
    os.path.dirname(__file__), "..", "sid_agent", "data", "profile.json"
)

# The public layer must never contain private context. This guard fails the
# build if private material ever leaks into the seed profile.
FORBIDDEN = [
    "sanskriti",
    "skrit",
    "girlfriend",
    "park glenn",
    "263-5932",
    "22145",
]


class TestProfile(unittest.TestCase):
    def test_loads_and_has_core_fields(self):
        p = Profile.load()
        self.assertEqual(p.get("name"), "Sid Vemula")
        self.assertEqual(p.get("graduation"), "May 2028")
        self.assertIn("CMSC132 Object-Oriented Programming II", p.courses())

    def test_public_layer_privacy_guard(self):
        with open(_PROFILE_JSON, "r", encoding="utf-8") as f:
            raw = f.read().lower()
        for token in FORBIDDEN:
            self.assertNotIn(token, raw, f"private token leaked into profile: {token}")
        data = json.loads(raw)
        self.assertNotIn("address", data)
        self.assertNotIn("phone", data)
        self.assertNotIn("email", data)


if __name__ == "__main__":
    unittest.main()
