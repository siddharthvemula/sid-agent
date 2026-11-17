"""Profile loading for SidAgent.

The profile is the agent's *public layer*: school, degree, courses,
projects, experience, skills, goals. It deliberately contains no private
context (relationships, family, contact details, inbox data). Private
layers can be added later as separate files, on Sid's explicit say-so.
"""
import json
import os

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "data", "profile.json")


class Profile:
    def __init__(self, data):
        self._data = data

    @classmethod
    def load(cls, path=None):
        with open(path or _DEFAULT_PATH, "r", encoding="utf-8") as f:
            return cls(json.load(f))

    def get(self, field, default=None):
        return self._data.get(field, default)

    def fields(self):
        return sorted(self._data.keys())

    def courses(self):
        return list(self._data.get("fall_2026_courses", []))

    def summary(self):
        lines = [
            f"{self.get('name')} - {self.get('class_status')}",
            f"{self.get('school')}",
            f"{self.get('degree')} - graduating {self.get('graduation')}",
        ]
        return "\n".join(lines)

    def to_dict(self):
        return dict(self._data)
