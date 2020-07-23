import apraw
import pytest

from banhammer.models import RedditItem, Subreddit, ReactionPayload


class TestReactionPayload:
    @pytest.mark.asyncio
    async def test_feed(self, reddit: apraw.Reddit, subreddit: Subreddit):
        sub = await reddit.subreddit("banhammerdemo")
        item = None

        async for s in sub.new():
            item = RedditItem(s, subreddit, "new")
            break

        payload = ReactionPayload()
        payload.feed(item, False, "Test", "🔥", "Test reply.")

        assert payload.item == item
        assert not payload.approved
        assert payload.user == "Test"
        assert payload.reply == "Test reply."
        assert payload.emoji == "🔥"

    @pytest.mark.asyncio
    async def test_get_message(self, reddit: apraw.Reddit, subreddit: Subreddit):
        sub = await reddit.subreddit("banhammerdemo")
        item = None

        async for s in sub.new():
            item = RedditItem(s, subreddit, "new")
            break

        payload = ReactionPayload()
        payload.feed(item, False, "Test", "🔥", "Test reply.")

        assert isinstance(await payload.get_message(), str)
