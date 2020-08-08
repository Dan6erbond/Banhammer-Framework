from typing import TYPE_CHECKING, Union

import apraw
import discord
from apraw.models import (Comment, Message, ModAction, ModmailConversation,
                          ModmailMessage, Submission, Subreddit)

from ..const import logger

if TYPE_CHECKING:
    from .subreddit import Subreddit


class RedditItem:

    def __init__(self, item: Union[Comment, ModmailConversation, ModmailMessage,
                                   Submission], subreddit: 'Subreddit', source: str):
        self.item = item
        self.id = item.id
        self.type = "submission" if isinstance(
            item, Submission) else "comment" if isinstance(
            item, Comment) else "modmail" if type(item) in [
            ModmailMessage, ModmailConversation] else "mod action"
        self.subreddit = subreddit
        self.source = source
        self._author = None

    def __repr__(self):
        return f"<{self.type.title()} id={self.id} source={self.source}>"

    async def get_message(self):
        return await self.subreddit.banhammer.message_builder.get_item_message(self)

    async def to_dict(self):
        return {
            "url": self.url,
            "author": await self.get_author_name(),
            "type": self.type,
            "source": self.source,
            "body": self.body
        }

    async def get_embed(self, *args, **kwargs):
        return await self.subreddit.banhammer.message_builder.get_item_embed(self, *args, **kwargs)

    def format_reply(self, reply: str):
        return self.subreddit.banhammer.message_builder.format_reply(self, reply)

    def get_ban_message(self, ban_duration: int):
        return self.subreddit.banhammer.message_builder.get_ban_message(self, ban_duration)

    async def get_author(self):
        if not self._author:
            if isinstance(self.item, ModAction):
                try:
                    self._author = await self.item.mod()
                except Exception as e:
                    logger.error(f"Failed to retrieve item author in {self.item}: {e}")
            elif not isinstance(self.item, ModmailConversation):
                try:
                    self._author = await self.item.author()
                except Exception as e:
                    logger.error(f"Failed to retrieve item author in {self.item}: {e}")
            else:
                self._author = self.item.authors[0]
        return self._author

    async def is_author_removed(self):
        author = await self.get_author()
        author_removed = not author
        if author and not isinstance(author, dict):
            author_removed = not hasattr(author, "name")
        elif author:
            author_removed = author.get("isDeleted", False)
        return author_removed

    async def get_author_name(self):
        if await self.is_author_removed():
            return "[deleted]"
        else:
            author = await self.get_author()
            if not isinstance(author, dict):
                return author.name
            else:
                return author["name"]

    @property
    def reactions(self):
        return self.subreddit.get_reactions(self.item)

    async def add_reactions(self, message: discord.Message):
        for r in self.reactions:
            try:
                await message.add_reaction(r.emoji)
            except Exception as e:
                logger.error(f"Failed to add reaction '{r.emoji}': {e}")
                continue

    def get_reaction(self, emoji: str):
        return self.subreddit.get_reaction(emoji, self.item)

    @property
    def url(self):
        return get_item_url(self.item)

    @property
    def body(self):
        if self.type == "submission":
            return self.item.selftext[:1021] + (self.item.selftext[1021:] and "...") or "Empty"
        elif self.type == "comment":
            return self.item.body[:1021] + (self.item.body[1021:] and "...")
        elif self.type == "modmail":
            return self.item.body_md[:1021] + (self.item.body_md[1021:] and "...")
        elif self.type == "mod action":
            return self.item.action


def get_item_url(item: RedditItem):
    if isinstance(item, Submission):
        return f"https://www.reddit.com/r/{item._data['subreddit']}/comments/{item.id}"
    elif isinstance(item, Comment):
        return f"https://www.reddit.com/r/{item._data['subreddit']}/comments/{item.link_id.replace('t3_', '')}/_/{item.id}"
    elif isinstance(item, ModmailConversation):
        return "https://mod.reddit.com/mail/all/" + item.id
    elif isinstance(item, ModmailMessage):
        return "https://mod.reddit.com/mail/all/" + item.conversation.id
    elif isinstance(item, Message):
        if item.was_comment:
            return f"https://www.reddit.com/r/{item._data['subreddit']}/comments/{item.link_id.replace('t3_', '')}/_/{item.id}"
        else:
            return "https://www.reddit.com/message/messages/{}" + str(item)
    elif isinstance(item, Subreddit):
        return "https://www.reddit.com/r/" + item.display_name
    return ""
