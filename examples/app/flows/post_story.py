from __future__ import annotations

from pydantic import BaseModel

from fastapi_cloudflow import Context, HttpStep, step, workflow


class StoryIn(BaseModel):
    topic: str
    mood: str
    author_id: int


class PostOut(BaseModel):
    id: int
    title: str
    body: str
    userId: int


class PostSummary(BaseModel):
    id: int
    slug: str
    short_title: str


@step(name="build-story")
async def build_story(ctx: Context, data: StoryIn) -> PostOut:
    title = f"{data.topic} in a {data.mood} mood"
    body = f"Once upon a time about {data.topic}"
    return PostOut(id=0, title=title, body=body, userId=data.author_id)


jp_create_post = HttpStep(
    name="create-post",
    input_model=PostOut,
    output_model=PostOut,
    method="POST",
    url="https://jsonplaceholder.typicode.com/posts",
)


@step(name="summarize-post")
async def summarize_post(ctx: Context, data: PostOut) -> PostSummary:
    slug = f"{data.userId}-{(data.title or '').lower().replace(' ', '-')[:24]}"
    short = (data.title or "")[:16]
    return PostSummary(id=data.id, slug=slug, short_title=short)


POST_STORY_FLOW = (workflow("post-story-flow") >> build_story >> jp_create_post >> summarize_post).build()
