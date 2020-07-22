import apraw
import pytest

from banhammer.models import Reaction, RedditItem, Subreddit


class TestSubreddit:
    @pytest.mark.asyncio
    async def test_load_reactions(self, subreddit: Subreddit):
        await subreddit.load_reactions()
        for r in subreddit.reactions:
            assert isinstance(r, Reaction)

    @pytest.mark.asyncio
    async def test_contact_url(self, subreddit: Subreddit):
        url = subreddit.get_contact_url()
        assert url == "https://www.reddit.com/message/compose/?to=/r/banhammerdemo"

    @pytest.mark.asyncio
    async def test_get_subreddit(self, subreddit: Subreddit):
        sub = await subreddit.get_subreddit()
        assert isinstance(sub, apraw.models.Subreddit)

    @pytest.mark.asyncio
    async def test_setup(self, subreddit: Subreddit):
        await subreddit.setup()
        assert isinstance(subreddit.get_status(), str)

    @pytest.mark.asyncio
    async def test_get_reactions(self, reddit: apraw.Reddit, subreddit: Subreddit):
        await subreddit.load_reactions()

        sub = await reddit.subreddit("banhammerdemo")
        item = None

        async for s in sub.new():
            item = RedditItem(s, subreddit, "new")
            break

        if item:
            for r in subreddit.get_reactions(item):
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
            emojis = [r.emoji for r in subreddit.get_reactions(item)]
            if emojis:
                reaction = subreddit.get_reaction(item, emojis[0])
                assert isinstance(reaction, Reaction)
