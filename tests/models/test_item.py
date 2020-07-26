import apraw
import discord
import pytest

from banhammer import Banhammer
from banhammer.models import RedditItem, Subreddit, Reaction


class TestRedditItem:
    @pytest.mark.asyncio
    async def test_get_message(self, reddit: apraw.Reddit, subreddit: Subreddit):
        sub = await reddit.subreddit("banhammerdemo")
        item = None

        async for s in sub.new():
            item = RedditItem(s, subreddit, "new")
            break

        if item:
            assert isinstance(await item.get_message(), str)

    @pytest.mark.asyncio
    async def test_get_embed(self, reddit: apraw.Reddit, subreddit: Subreddit):
        sub = await reddit.subreddit("banhammerdemo")
        item = None

        async for s in sub.new():
            item = RedditItem(s, subreddit, "new")
            break

        if item:
            assert isinstance(await item.get_embed(), discord.Embed)

    @pytest.mark.asyncio
    async def test_get_author(self, reddit: apraw.Reddit, subreddit: Subreddit):
        sub = await reddit.subreddit("banhammerdemo")
        item = None
        author = None

        async for s in sub.new():
            item = RedditItem(s, subreddit, "new")
            author = await s.author()
            break

        if item:
            a = await item.get_author()
            assert a.name.lower() == author.name.lower()

    @pytest.mark.asyncio
    async def test_is_author_removed(self, reddit: apraw.Reddit, subreddit: Subreddit, banhammer: Banhammer):
        sub = await reddit.subreddit("banhammerdemo")
        item = None

        async for s in sub.new():
            item = RedditItem(s, subreddit, "new")
            break

        if item:
            assert not await item.is_author_removed()

        url = "https://www.reddit.com/r/banhammerdemo/comments/c66rdl"
        item = await banhammer.get_item(url)

        if item:
            assert await item.is_author_removed()

    @pytest.mark.asyncio
    async def test_get_author_name(self, reddit: apraw.Reddit, subreddit: Subreddit):
        sub = await reddit.subreddit("banhammerdemo")
        item = None
        author = None

        async for s in sub.new():
            item = RedditItem(s, subreddit, "new")
            author = await s.author()
            break

        if item:
            author_name = await item.get_author_name()
            assert author_name.lower() == author.name.lower()

    @pytest.mark.asyncio
    async def test_get_reactions(self, reddit: apraw.Reddit, subreddit: Subreddit):
        await subreddit.load_reactions()

        sub = await reddit.subreddit("banhammerdemo")
        item = None

        async for s in sub.new():
            item = RedditItem(s, subreddit, "new")
            break

        if item:
            for r in item.get_reactions():
                assert isinstance(r, Reaction)

    @pytest.mark.asyncio
    async def test_get_reaction(self, reddit: apraw.Reddit, subreddit: Subreddit):
        await subreddit.load_reactions()

        sub = await reddit.subreddit("banhammerdemo")
        item = None

        async for s in sub.new():
            item = RedditItem(s, subreddit, "new")
            break

        if item:
            emojis = [r.emoji for r in item.get_reactions()]
            if emojis:
                reaction = item.get_reaction(emojis[0])
                assert reaction == item.get_reactions()[0]

    @pytest.mark.asyncio
    async def test_url(self, reddit: apraw.Reddit, subreddit: Subreddit):
        await subreddit.load_reactions()

        sub = await reddit.subreddit("banhammerdemo")
        item = None

        async for s in sub.new():
            item = RedditItem(s, subreddit, "new")
            break

        if item:
            assert item.url in s.url

    @pytest.mark.asyncio
    async def test_format_reply(self, reddit: apraw.Reddit, subreddit: Subreddit, banhammer: Banhammer):
        sub = await reddit.subreddit("banhammerdemo")
        item = None

        async for s in sub.new():
            item = RedditItem(s, subreddit, "new")
            break

        assert item

        if item:
            assert isinstance(item.format_reply("Test reply."), str)
