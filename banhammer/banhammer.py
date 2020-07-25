import asyncio
import json
import logging
import os
import re

import apraw
import discord
from apraw.utils import ExponentialCounter

from .models import MessageBuilder, ReactionHandler, Subreddit
from .utils import reddit_helper

banhammer_purple = discord.Colour(0).from_rgb(207, 206, 255)
logger = logging.getLogger("banhammer")


class Banhammer:

    def __init__(self, reddit: apraw.Reddit, max_loop_time: int = 16, bot: discord.Client = None, embed_color: discord.Colour = banhammer_purple,
                 change_presence: bool = False, message_builder: MessageBuilder = MessageBuilder(), reaction_handler: ReactionHandler = ReactionHandler()):
        self.reddit = reddit
        self.subreddits = list()
        self.loop = asyncio.get_event_loop()

        self.item_funcs = list()
        self.action_funcs = list()

        self.max_loop_time = max_loop_time

        self.message_builder = message_builder
        self.reaction_handler = reaction_handler
        self.bot = bot
        self.embed_color = embed_color
        self.change_presence = change_presence

    async def add_subreddits(self, *subs):
        for sub in subs:
            if not isinstance(sub, Subreddit):
                sub = Subreddit(self, subreddit=str(sub))
                await sub.load_reactions()
            self.subreddits.append(sub)

    def remove_subreddit(self, subreddit):
        subreddit = str(subreddit).lower().replace("r/", "").replace("/", "")
        for sub in self.subreddits:
            sub = str(sub).lower().replace("r/", "").replace("/", "")
            if sub == subreddit:
                self.subreddits.remove(sub)
                return True
        return False

    def new(self, **kwargs):
        def assign(func):
            self.add_new_func(func, **kwargs)
            return func

        return assign

    def add_new_func(self, func, **kwargs):
        self.add_items_func(func, "get_new", **kwargs)

    def comments(self, **kwargs):
        def assign(func):
            self.add_comments_func(func, **kwargs)
            return func

        return assign

    def add_comments_func(self, func, **kwargs):
        self.add_items_func(func, "get_comments", **kwargs)

    def mail(self, **kwargs):
        def assign(func):
            self.add_mail_func(func, **kwargs)
            return func

        return assign

    def add_mail_func(self, func, **kwargs):
        self.add_items_func(func, "get_mail", **kwargs)

    def queue(self, **kwargs):
        def assign(func):
            self.add_queue_func(func, **kwargs)
            return func

        return assign

    def add_queue_func(self, func, **kwargs):
        self.add_items_func(func, "get_queue", **kwargs)

    def reports(self, **kwargs):
        def assign(func):
            self.add_report_func(func, **kwargs)
            return func

        return assign

    def add_report_func(self, func, **kwargs):
        self.add_items_func(func, "get_reports", **kwargs)

    def add_items_func(self, func, sub_func, **kwargs):
        if asyncio.iscoroutinefunction(func):
            self.item_funcs.append({
                "func": func,
                "sub": kwargs["subreddit"] if "subreddit" in kwargs else None,
                "sub_func": sub_func
            })

    async def send_items(self):
        counter = ExponentialCounter(self.max_loop_time)

        while True:
            found = False

            if self.bot and self.change_presence:
                try:
                    watching = discord.Activity(type=discord.ActivityType.watching, name="Reddit")
                    await self.bot.change_presence(activity=watching)
                except Exception as e:
                    logger.error(e)

            for func in self.item_funcs:
                if func["sub"]:
                    subs = [sub for sub in self.subreddits if str(sub).lower() == func["sub"].lower()]
                else:
                    subs = self.subreddits
                for sub in subs:
                    sub_func = getattr(sub, func["sub_func"])
                    try:
                        async for post in sub_func():
                            found = True
                            await func["func"](post)
                    except Exception as e:
                        logger.error(e)

            for func in self.action_funcs:
                if func["sub"]:
                    subs = [sub for sub in self.subreddits if str(sub).lower() == func["sub"].lower()]
                else:
                    subs = self.subreddits
                for sub in subs:
                    try:
                        async for action in sub.get_mod_actions(func["mods"]):
                            found = True
                            await func["func"](action)
                    except Exception as e:
                        logger.error(e)

            if self.bot is not None and self.change_presence:
                try:
                    await self.bot.change_presence(activity=None)
                except Exception as e:
                    logger.error(e)

            if not found:
                wait_time = counter.count()
            else:
                wait_time = counter.reset()

            await asyncio.sleep(wait_time)

    def mod_actions(self, *args, **kwargs):
        def assign(func):
            self.add_mod_actions_func(func, *args, **kwargs)
            return func

        return assign

    def add_mod_actions_func(self, func, *args, **kwargs):
        if asyncio.iscoroutinefunction(func):
            self.action_funcs.append({
                "func": func,
                "mods": kwargs["mods"] if "mods" in kwargs else list(args),
                "sub": kwargs["subreddit"] if "subreddit" in kwargs else None
            })

    async def get_item(self, c):
        s = str(c) if not isinstance(c, discord.Embed) else json.dumps(c.to_dict())
        return await reddit_helper.get_item(self.reddit, self.subreddits, s)

    def get_reactions_embed(self):
        embed = discord.Embed(
            colour=self.embed_color
        )
        embed.title = "Configured reactions"
        for sub in self.subreddits:
            embed.add_field(name="/r/" + str(sub),
                            value="\n".join([str(r) for r in sub.reactions]),
                            inline=False)
        return embed

    def get_subreddits_embed(self):
        embed = discord.Embed(
            colour=self.embed_color
        )
        embed.title = "Subreddits' statuses"
        embed.description = "\n".join([s.get_status() for s in self.subreddits])
        return embed

    def run(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(dir_path + "/WELCOME.md") as f:
            print("")
            BOLD = '\033[1m'
            END = '\033[0m'
            print(re.sub(r"\*\*(.+)\*\*", r"{}\1{}".format(BOLD, END), f.read()))
            print("")

        if len(self.item_funcs) > 0 or len(self.action_funcs) > 0:
            self.loop.create_task(self.send_items())
