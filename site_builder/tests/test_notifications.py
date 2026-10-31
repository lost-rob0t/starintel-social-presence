import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[2] / "scripts" / "notify_new_posts.py"
SPEC = importlib.util.spec_from_file_location("notify_new_posts", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
message = MODULE.message
post_metadata = MODULE.post_metadata


def test_post_metadata_accepts_published_post(tmp_path: Path) -> None:
    post = tmp_path / "post.org"
    post.write_text(
        "#+title: A real post\n#+slug: real-post\n#+description: Evidence first.\n#+status: POST\n",
        encoding="utf-8",
    )
    assert post_metadata(post) == {
        "title": "A real post",
        "slug": "real-post",
        "description": "Evidence first.",
    }


def test_post_metadata_ignores_draft(tmp_path: Path) -> None:
    post = tmp_path / "draft.org"
    post.write_text("#+title: Draft\n#+status: DRAFT\n", encoding="utf-8")
    assert post_metadata(post) is None


def test_post_metadata_requires_public_fields(tmp_path: Path) -> None:
    post = tmp_path / "broken.org"
    post.write_text("#+title: Broken\n#+status: POST\n", encoding="utf-8")
    with pytest.raises(ValueError):
        post_metadata(post)


def test_message_links_to_canonical_post() -> None:
    text = message(
        {"title": "Post", "slug": "post", "description": "Description"},
        "https://blog.starintel.actor",
    )
    assert text.endswith("https://blog.starintel.actor/post.html")
