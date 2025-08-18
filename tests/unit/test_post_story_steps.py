from __future__ import annotations

from fastapi.testclient import TestClient
from main import app


def test_build_story_and_summarize() -> None:
    c = TestClient(app)

    story = {"topic": "AI", "mood": "playful", "author_id": 7}
    r1 = c.post(
        "/steps/build-story",
        headers={"X-Workflow-Name": "unit"},
        json=story,
    )
    assert r1.status_code == 200
    post = r1.json()
    assert post["title"]
    assert post["userId"] == 7

    # summarize-post expects PostOut shape
    r2 = c.post(
        "/steps/summarize-post",
        headers={"X-Workflow-Name": "unit", "X-Workflow-Run-Id": "test"},
        json=post,
    )
    assert r2.status_code == 200
    summary = r2.json()
    assert "slug" in summary and "short_title" in summary
