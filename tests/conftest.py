import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.contracts import SessionTrace  # noqa: E402

FIX = os.path.join(ROOT, "demo", "fixtures")


@pytest.fixture
def hero():
    return SessionTrace.from_dict(json.load(open(os.path.join(FIX, "hero_attack.json"))))


@pytest.fixture
def clean():
    return SessionTrace.from_dict(json.load(open(os.path.join(FIX, "clean_session.json"))))
