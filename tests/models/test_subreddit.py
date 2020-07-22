import apraw
import pytest

from banhammer.models import Reaction, Subreddit


class TestSubreddit:
    @pytest.mark.asyncio
    async def test_load_reactions(self, subreddit: Subreddit):
        await subreddit.load_reactions()
        for r in sub.reactions:
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
