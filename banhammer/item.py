import apraw
import discord
from apraw.models import (Comment, Message, ModmailConversation,
                          ModmailMessage, Submission, Subreddit)


class RedditItem:

    def __init__(self, item, subreddit, source):
        self.item = item
        self.id = item.id
        self.type = "submission" if isinstance(
            item, Submission) else "comment" if isinstance(
            item, Comment) else "modmail" if type(item) in [
            ModmailMessage, ModmailConversation] else "mod action"
        self.subreddit = subreddit
        self.source = source

    def __str__(self):
        return self.subreddit.banhammer.message_builder.get_item_message(self)

    def get_embed(self, embed_color: discord.Color = None):
        return self.subreddit.banhammer.message_builder.get_item_embed(self, embed_color)

    def is_removed(self):
        removed = self.item is None
        try:
            id = self.item.id
        except Exception:
            removed = True
        return removed

    def get_author(self):
        return self.item.author if not isinstance(
            self.item, ModmailConversation) else self.item.authors[0]

    def is_author_removed(self):
        author = self.get_author()
        author_removed = author is None
        try:
            name = author.name
        except Exception:
            author_removed = True
        return author_removed

    def get_author_name(self):
        if self.is_author_removed():
            return "[deleted]"
        else:
            return self.get_author().name

    def get_reactions(self):
        reactions = self.subreddit.get_reactions(self.item)
        for r in reactions:
            r.item = self
        return reactions

    async def add_reactions(self, message):
        for r in self.get_reactions():
            try:
                await message.add_reaction(r.emoji)
            except Exception as e:
                print(e)
                continue

    def get_reaction(self, emoji):
        r = self.subreddit.get_reaction(emoji, self.item)
        r.item = self
        return r

    def get_url(self):
        return get_item_url(self.item)


def get_item_url(item):
    if isinstance(item, Submission):
        return f"https://www.reddit.com/r/{item.subreddit}/comments/{item}"
    elif isinstance(item, Comment):
        return f"https://www.reddit.com/r/{item.subreddit}/comments/{item.submission}/_/{item}"
    elif isinstance(item, ModmailConversation):
        return "https://mod.reddit.com/mail/all/" + item.id
    elif isinstance(item, ModmailMessage):
        return "https://mod.reddit.com/mail/all/" + item.conversation.id
    elif isinstance(item, Message):
        if item.was_comment:
            return f"https://www.reddit.com/r/{item.subreddit}/comments/{item.submission}/_/{item}"
        else:
            return "https://www.reddit.com/message/messages/{}" + str(item)
    elif isinstance(item, Subreddit):
        return "https://www.reddit.com/r/" + item.display_name
    return ""
