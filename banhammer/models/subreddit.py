import os
from typing import TYPE_CHECKING, List

from apraw.utils import BoundedSet

from ..const import logger
from .item import RedditItem
from .reaction import get_reactions

if TYPE_CHECKING:
    from ..banhammer import Banhammer


class Subreddit:

    def __init__(self, bh: 'Banhammer', **opts):
        self.banhammer = bh
        self.reddit = bh.reddit

        self.name = opts["subreddit"] if "subreddit" in opts else ""
        self.name = self.name.replace("r/", "").replace("/", "")

        self.stream_new = opts.get("stream_new", True)
        self.stream_comments = opts.get("stream_comments", False)
        self.stream_reports = opts.get("stream_reports", True)
        self.stream_mail = opts.get("stream_mail", True)
        self.stream_queue = opts.get("stream_queue", True)
        self.stream_mod_actions = opts.get("stream_mod_actions", True)

        self._new_ids = BoundedSet(301)
        self._comment_ids = BoundedSet(301)
        self._report_ids = BoundedSet(301)
        self._mail_ids = BoundedSet(301)
        self._queue_ids = BoundedSet(301)
        self._mod_action_ids = BoundedSet(301)

        self._skip_new = True
        self._skip_comments = True
        self._skip_reports = True
        self._skip_mail = True
        self._skip_queue = True
        self._skip_mod_actions = True

        self._subreddit = None

        self.custom_emotes = opts.get("custom_emotes", True)

        path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reactions.yaml"))
        with open(path, encoding="utf8") as f:
            content = f.read()
            self.reactions = get_reactions(content)["reactions"]

    def __str__(self):
        return self.name

    @property
    def status(self):
        str = "/r/" + self.name

        if self.stream_new:
            str += " | New Posts"
        if self.stream_comments:
            str += " | Comments"
        if self.stream_reports:
            str += " | Reports"
        if self.stream_mail:
            str += " | Mod-Mail"
        if self.stream_queue:
            str += " | Mod-Queue"

        return str

    @property
    def contact_url(self):
        return "https://www.reddit.com/message/compose/?to=/r/" + self.name

    async def get_subreddit(self):
        if not self._subreddit:
            self._subreddit = await self.reddit.subreddit(self.name)
        return self._subreddit

    async def setup(self):
        subreddit = await self.get_subreddit()
        settings = await subreddit.mod.settings()
        self.stream_new = settings.spam_links != "all" and settings.spam_selfposts != "all"
        self.stream_comments = settings.spam_comments == "all"
        self.stream_queue = settings.spam_links == "all" or settings.spam_selfposts == "all"

    async def load_reactions(self):
        subreddit = await self.get_subreddit()
        loaded = False

        if self.custom_emotes:
            try:
                reaction_page = await subreddit.wiki.page("banhammer-reactions")
                reacts = get_reactions(reaction_page.content_md)["reactions"]
                if reacts:
                    self.reactions = reacts
                    loaded = True
            except Exception as e:
                logger.error(f"Couldn't load wikipage: {e}")

        if not loaded:
            path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reactions.yaml"))
            with open(path, encoding="utf8") as f:
                try:
                    await subreddit.wiki.create("banhammer-reactions", f.read(), "Reactions not found")
                except Exception as e:
                    logger.error(f"Couldn't create wikipage: {e}")

    async def get_reactions_embed(self, *args, **kwargs):
        return await self.banhammer.message_builder.get_subreddit_reactions_embed(self, *args, **kwargs)

    def get_reactions(self, item: RedditItem):
        return [r for r in self.reactions if r.eligible(item)]

    def get_reaction(self, emoji: str, item: RedditItem):
        for reaction in self.get_reactions(item):
            if reaction.emoji == emoji:
                return reaction

    async def get_new(self):
        subreddit = await self.get_subreddit()
        submissions = [s async for s in subreddit.new()]
        for submission in reversed(submissions):
            if not submission:
                continue
            if submission.id in self._new_ids:
                continue

            self._new_ids.add(submission.id)

            if not self._skip_new:
                item = RedditItem(submission, self, "new")
                yield item

        self._skip_new = False

    async def get_comments(self):
        subreddit = await self.get_subreddit()
        comments = [s async for s in subreddit.comments()]
        for comment in reversed(comments):
            if not comment:
                continue
            if comment.id in self._comment_ids:
                continue

            self._comment_ids.add(comment.id)

            if not self._skip_comments:
                item = RedditItem(comment, self, "new")
                yield item

        self._skip_comments = False

    async def get_reports(self):
        subreddit = await self.get_subreddit()
        items = [s async for s in subreddit.mod.reports()]
        for item in reversed(items):
            if not item:
                continue
            if item.id in self._report_ids:
                continue

            self._report_ids.add(item.id)

            if not self._skip_reports:
                item = RedditItem(item, self, "reports")
                yield item

        self._skip_reports = False

    async def get_mail(self):
        subreddit = await self.get_subreddit()
        conversations = [s async for s in subreddit.modmail.conversations()]
        for conversation in reversed(conversations):
            async for message in conversation.messages():
                if not message:
                    continue
                if message.id in self._mail_ids:
                    continue

                self._mail_ids.add(message.id)

                if not self._skip_mail:
                    message = RedditItem(message, self, "modmail")
                    yield message

        self._skip_mail = False

    async def get_queue(self):
        subreddit = await self.get_subreddit()
        items = [s async for s in subreddit.mod.modqueue()]
        for item in reversed(items):
            if not item:
                continue
            if item.id in self._queue_ids:
                continue

            self._queue_ids.add(item.id)

            if not self._skip_queue:
                item = RedditItem(item, self, "queue")
                yield item

        self._skip_queue = False

    async def get_mod_actions(self, mods: List[str] = list()):
        subreddit = await self.get_subreddit()
        mods = [m.lower() for m in mods]
        actions = [s async for s in subreddit.mod.log()]
        for action in reversed(actions):
            if not action:
                continue
            if action.id in self._mod_action_ids:
                continue
            if action._data["mod"].lower() not in mods and mods:
                continue

            self._mod_action_ids.add(action.id)

            if not self._skip_mod_actions:
                action = RedditItem(action, self, "log")
                yield action

        self._skip_mod_actions = False
