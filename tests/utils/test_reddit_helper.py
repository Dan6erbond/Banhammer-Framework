import apraw
import pytest

from banhammer.models import RedditItem, Subreddit, ReactionPayload
from banhammer.utils import reddit_helper


class TestRedditHelper:
    @pytest.mark.asyncio
    async def test_get_item(self, reddit: apraw.Reddit, subreddit: Subreddit):
        url = "https://www.reddit.com/r/banhammerdemo/comments/hy5p58/test_post/"
        item = await reddit_helper.get_item(reddit, [subreddit], url)
        assert item.type == "submission"

        url = "https://www.reddit.com/r/banhammerdemo/comments/hy5p58/test_post/fzalfre"
        item = await reddit_helper.get_item(reddit, [subreddit], url)
        assert item.type == "comment"

        url = "https://mod.reddit.com/mail/all/fqtr0"
        item = await reddit_helper.get_item(reddit, [subreddit], url)
        assert item.type == "modmail"
