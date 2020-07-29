import pytest

from banhammer import Banhammer
from banhammer.models import EventHandler, RedditItem, ItemAttribute


class TestBanhammer:
    @pytest.mark.asyncio
    async def test_banhammer_meta(self):
        handle_new_called = 0
        handle_comments_called = 0
        handle_mod_actions_called = 0

        class CustomBanhammer(Banhammer):
            @EventHandler.new()
            @EventHandler.filter(ItemAttribute.AUTHOR, "Dan6erbond")
            @EventHandler.filter(ItemAttribute.SUBREDDIT, "banhammerdemo")
            async def handle_new(self, item: RedditItem):
                nonlocal handle_new_called
                assert self, not item
                handle_new_called += 1

            @EventHandler.mod_actions("Anti-Evil Operations")
            async def handle_mod_actions(self, item: RedditItem):
                nonlocal handle_mod_actions_called
                assert self, not item
                handle_mod_actions_called += 1

        cb = CustomBanhammer(None)
        assert len(cb._event_handlers[0]._filters) == 2
        assert len(cb._event_handlers[1]._filters[0]._values) == 1

        @cb.comments()
        async def handle_comments(item: RedditItem):
            nonlocal handle_comments_called
            assert not item
            handle_comments_called += 1

        for event_handler in cb._event_handlers:
            if event_handler._takes_self:
                await event_handler._callback(cb, None)
            else:
                await event_handler._callback(None)

        assert handle_new_called == 1
        assert handle_comments_called == 1
        assert handle_mod_actions_called == 1
