from typing import List

from apraw.utils import BoundedSet

from . import reaction
from .item import RedditItem


class Subreddit:

    def __init__(self, bh, **opts):
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
        self.reactions = list()

    def __str__(self):
        return self.name

    def get_status(self):
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

    def get_contact_url(self):
        return "https://www.reddit.com/message/compose/?to=/r/" + self.name

    async def get_subreddit(self):
        if not self._subreddit:
            self._subreddit = await self.banhammer.reddit.subreddit(self.name)
        return self._subreddit

    async def setup(self):
        subreddit = await self.get_subreddit()
        settings = await subreddit.mod.settings()
        self.stream_new = settings.spam_links != "all" and settings.spam_selfposts != "all"
        self.stream_comments = settings.spam_comments == "all"
        self.stream_queue = settings.spam_links == "all" or settings.spam_selfposts == "all"

    async def load_reactions(self):
        subreddit = await self.get_subreddit()
        if self.custom_emotes:
            try:
                reaction_page = await subreddit.wiki.page("banhammer-reactions")
                reacts = reaction.get_reactions(reaction_page.content_md)["reactions"]
                if len(reacts) > 0:
                    self.reactions = reacts
            except Exception as e:
                print(type(e), e)

        if not len(self.reactions) > 0:
            dir_path = os.path.dirname(os.path.realpath(__file__))
            with open(dir_path + "/reactions.yaml", encoding="utf8") as f:
                content = f.read()
                self.reactions = reaction.get_reactions(content)["reactions"]
                try:
                    subreddit.wiki.create("banhammer-reactions", content, reason="Reactions not found")
                except Exception as e:
                    print(e)

    def get_reactions(self, item):
        _r = list()
        for reaction in self.reactions:
            if reaction.eligible(item):
                _r.append(reaction)
        return _r

    def get_reaction(self, emoji, item):
        for reaction in self.get_reactions(item):
            if reaction.emoji == emoji:
                return reaction

    async def get_new(self):
        subreddit = await self.get_subreddit()
        submissions = [s async for s in subreddit.new()]
        for submission in reversed(submissions):
            if submission.id in self._new_ids:
                continue

            self._new_ids.add(submission.id)

            if not self._skip_new:
                item = RedditItem(submission, self, "new")
                yield item

        self._skip_new = False

    async def get_comments(self):
        subreddit = await self.get_subreddit()
        comments = [s async for s in subreddit.comments(limit=250 if not self._skip_comments else 100)]
        for comment in reversed(comments):
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
        actions = [s async for s in subreddit.mod.log(limit=None if not self._skip_mod_actions else 100)]
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
