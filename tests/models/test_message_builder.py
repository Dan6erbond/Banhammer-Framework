import apraw
import discord
import pytest

from banhammer import Banhammer
from banhammer.models import ReactionPayload, RedditItem, Subreddit


class TestMessageBuilder:
    @pytest.mark.asyncio
    async def test_get_item_message(self, reddit: apraw.Reddit, subreddit: Subreddit, banhammer: Banhammer):
        sub = await reddit.subreddit("banhammerdemo")
        item = None

        async for s in sub.new():
            item = RedditItem(s, subreddit, "new")
            break

        if item:
            assert isinstance(await banhammer.message_builder.get_item_message(item), str)

    @pytest.mark.asyncio
    async def test_get_item_embed(self, reddit: apraw.Reddit, subreddit: Subreddit, banhammer: Banhammer):
        sub = await reddit.subreddit("banhammerdemo")
        item = None

        async for s in sub.new():
            item = RedditItem(s, subreddit, "new")
            break

        if item:
            assert isinstance(await banhammer.message_builder.get_item_embed(item), discord.Embed)

    @pytest.mark.asyncio
    async def test_get_ban_message(self, reddit: apraw.Reddit, subreddit: Subreddit, banhammer: Banhammer):
        sub = await reddit.subreddit("banhammerdemo")
        item = None

        async for s in sub.new():
            item = RedditItem(s, subreddit, "new")
            break

        if item:
            assert isinstance(banhammer.message_builder.get_ban_message(item, 10), str)
