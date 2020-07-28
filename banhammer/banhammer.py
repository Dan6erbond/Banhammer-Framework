import asyncio
import json
import os
import re
from typing import Awaitable, Callable, Union

import apraw
import discord
from apraw.utils import ExponentialCounter

from .const import BANHAMMER_PURPLE, logger
from .models import MessageBuilder, ReactionHandler, RedditItem, Subreddit
from .utils import reddit_helper


class Banhammer:
    """
    The main Banhammer class that manages the event loop to poll Reddit and forward items to configured callables.
    """

    def __init__(self, reddit: apraw.Reddit, max_loop_time: int = 16, bot: discord.Client = None, embed_color: discord.Colour = BANHAMMER_PURPLE,
                 change_presence: bool = False, message_builder: MessageBuilder = MessageBuilder(), reaction_handler: ReactionHandler = ReactionHandler()):
        """
        Create a Banhammer instance.

        Parameters
        ----------
        reddit : apraw.Reddit
            The Reddit instance with which Subreddits are constructed and requests are made.
        max_loop_time : int, optional
            The maximum number of seconds to wait in between polls if no items were retrieved, by default 16.
        bot : discord.Client, optional
            The discord.Client in case presence should be changed, by default ``None``.
        embed_color : discord.Colour, optional
            The color to use for generated embeds, by default rgb(207, 206, 255).
        change_presence : bool, optional
            Whether the client's presence should be changed to "Watching Reddit" when polls are being performed, by default False
        message_builder : MessageBuilder, optional
            An instance of :class:`~banhammer.models.MessageBuilder` which is used by items to generate their embeds and such,
            by default MessageBuilder().
        reaction_handler : ReactionHandler, optional
            An instance of :class:`~banhammer.models.ReactionHandler` which handles reactions and feeds
            :class:`~banhammer.models.ReactionPayload`, by default ReactionHandler().
        """
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
        """
        Add subreddits for Banhammer to poll in its loop.

        If the given subreddit isn't of type :class:`~banhammer.models.Subreddit`, Banhammer will
        convert it and load the reactions / add default ones to the wiki using the
        :meth:`~banhammer.models.Subreddit.load_reactions` method.

        Parameters
        ----------
        *subs : Tuple[Subreddit]
            The *args subreddits to be added.
        """
        for sub in subs:
            if not isinstance(sub, Subreddit):
                sub = Subreddit(self, subreddit=str(sub))
                await sub.load_reactions()
            self.subreddits.append(sub)

    def remove_subreddit(self, subreddit: Union[Subreddit, apraw.models.Subreddit, str]):
        """
        Remove a subreddit from Banhammer's list.

        Parameters
        ----------
        subreddit : Union[Subreddit, apraw.models.Subreddit, str]
            The subreddit or the name of a subreddit to be removed.

        Returns
        -------
        removed : bool
            Whether a subreddit was found and removed.
        """
        subreddit = str(subreddit).lower().replace("r/", "").replace("/", "")
        for sub in self.subreddits:
            sub = str(sub).lower().replace("r/", "").replace("/", "")
            if sub == subreddit:
                self.subreddits.remove(sub)
                return True
        return False

    def new(self, **kwargs):
        """
        A decorator to subscribe to new posts with the given function.

        The decorator can be used like this:

        .. code-block:: python3

            @bh.new()
            async def handle_new(item: RedditItem):
                pass
        """
        def assign(func: Callable[[RedditItem], Awaitable[None]]):
            self.add_new_func(func, **kwargs)
            return func

        return assign

    def add_new_func(self, func: Callable[[RedditItem], Awaitable[None]], **kwargs):
        """
        Add a function to handle new posts.

        Parameters
        ----------
        func : Callable[[RedditItem], Awaitable[None]]
            The function that will be called when new posts are made.
        subreddit : str or Subreddit
            The subreddit to poll with this function.
        """
        self.add_items_func(func, "get_new", **kwargs)

    def comments(self, **kwargs):
        """
        A decorator to subscribe to comments with the given function.

        The decorator can be used like this:

        .. code-block:: python3

            @bh.comments()
            async def handle_comments(item: RedditItem):
                pass
        """
        def assign(func: Callable[[RedditItem], Awaitable[None]]):
            self.add_comments_func(func, **kwargs)
            return func

        return assign

    def add_comments_func(self, func: Callable[[RedditItem], Awaitable[None]], **kwargs):
        """
        Add a function to handle comments.

        Parameters
        ----------
        func : Callable[[RedditItem], Awaitable[None]]
            The function that will be called when comments are made.
        subreddit : str or Subreddit
            The subreddit to poll with this function.
        """
        self.add_items_func(func, "get_comments", **kwargs)

    def mail(self, **kwargs):
        """
        A decorator to subscribe to modmail with the given function.

        The decorator can be used like this:

        .. code-block:: python3

            @bh.mail()
            async def handle_mail(item: RedditItem):
                pass
        """
        def assign(func: Callable[[RedditItem], Awaitable[None]]):
            self.add_mail_func(func, **kwargs)
            return func

        return assign

    def add_mail_func(self, func: Callable[[RedditItem], Awaitable[None]], **kwargs):
        """
        Add a function to handle modmail.

        Parameters
        ----------
        func : Callable[[RedditItem], Awaitable[None]]
            The function that will be called when modmail are made.
        subreddit : str or Subreddit
            The subreddit to poll with this function.
        """
        self.add_items_func(func, "get_mail", **kwargs)

    def queue(self, **kwargs):
        """
        A decorator to subscribe to unmoderated posts with the given function.

        The decorator can be used like this:

        .. code-block:: python3

            @bh.queue()
            async def handle_queue(item: RedditItem):
                pass
        """
        def assign(func: Callable[[RedditItem], Awaitable[None]]):
            self.add_queue_func(func, **kwargs)
            return func

        return assign

    def add_queue_func(self, func: Callable[[RedditItem], Awaitable[None]], **kwargs):
        """
        Add a function to handle unmoderated posts.

        Parameters
        ----------
        func : Callable[[RedditItem], Awaitable[None]]
            The function that will be called when unmoderated posts are made.
        subreddit : str or Subreddit
            The subreddit to poll with this function.
        """
        self.add_items_func(func, "get_queue", **kwargs)

    def reports(self, **kwargs):
        """
        A decorator to subscribe to reported posts with the given function.

        The decorator can be used like this:

        .. code-block:: python3

            @bh.reports()
            async def handle_reports(item: RedditItem):
                pass
        """
        def assign(func: Callable[[RedditItem], Awaitable[None]]):
            self.add_report_func(func, **kwargs)
            return func

        return assign

    def add_report_func(self, func: Callable[[RedditItem], Awaitable[None]], **kwargs):
        """
        Add a function to handle reported posts.

        Parameters
        ----------
        func : Callable[[RedditItem], Awaitable[None]]
            The function that will be called when reported posts are made.
        subreddit : str or Subreddit
            The subreddit to poll with this function.
        """
        self.add_items_func(func, "get_reports", **kwargs)

    def add_items_func(self, func: Callable[[RedditItem], Awaitable[None]], sub_func: str, **kwargs):
        """
        Add a function to handle the items from a specific generator in the
        :class:`~banhammer.models.Subreddit` class.

        Parameters
        ----------
        func : Callable[[RedditItem], Awaitable[None]]
            The function that will be called when items are retrieved.
        sub_func : str
            The name of the generator found in the :class:`~banhammer.models.Subreddit` class.
        subreddit : str or Subreddit
            The subreddit to poll with this function.
        """
        if asyncio.iscoroutinefunction(func):
            self.item_funcs.append({
                "func": func,
                "sub": kwargs["subreddit"] if "subreddit" in kwargs else None,
                "sub_func": sub_func
            })

    async def send_items(self):
        """
        Start the loop to poll Reddit and send items.
        """
        counter = ExponentialCounter(self.max_loop_time)

        while True:
            found = False

            if self.bot and self.change_presence:
                try:
                    watching = discord.Activity(type=discord.ActivityType.watching, name="Reddit")
                    await self.bot.change_presence(activity=watching)
                except Exception as e:
                    logger.error(f"Failed to change bot presence: {e}")

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
                        logger.error(f"Failed to retrieve post from {func['sub_func']} in {sub}: {e}")

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
                        logger.error(f"Failed to retrieve mod action from {sub}: {e}")

            if self.bot is not None and self.change_presence:
                try:
                    await self.bot.change_presence(activity=None)
                except Exception as e:
                    logger.error(f"Failed to change bot presence: {e}")

            if not found:
                wait_time = counter.count()
            else:
                wait_time = counter.reset()

            await asyncio.sleep(wait_time)

    def mod_actions(self, *args, **kwargs):
        """
        A decorator to subscribe to mod actions with the given function.

        The decorator can be used like this, arguments passed will be
        used as the name of moderators to search for if given:

        .. code-block:: python3

            @bh.mod_actions("Anti-Evil Operations")
            async def handle_mod_actions(item: RedditItem):
                pass
        """
        def assign(func: Callable[[RedditItem], Awaitable[None]]):
            self.add_mod_actions_func(func, *args, **kwargs)
            return func

        return assign

    def add_mod_actions_func(self, func: Callable[[RedditItem], Awaitable[None]], *args, **kwargs):
        """
        Add a function to handle mod actions.

        Parameters
        ----------
        func : Callable[[RedditItem], Awaitable[None]]
            The function that will be called when mod actions are made.
        mods : Tuple[str]
            Moderators to search for if specified.
        subreddit : str or Subreddit
            The subreddit to poll with this function.
        """
        if asyncio.iscoroutinefunction(func):
            self.action_funcs.append({
                "func": func,
                "mods": kwargs["mods"] if "mods" in kwargs else list(args),
                "sub": kwargs["subreddit"] if "subreddit" in kwargs else None
            })

    async def get_item(self, c: Union[str, discord.Embed]):
        """
        Retrieve a :class:`banhammer.models.RedditItem` from a message or embed.

        Parameters
        ----------
        c : Union[str, discord.Embed]
            The message contents or embed to parse.

        Returns
        -------
        item: RedditItem
            The item found by its URL in the message or embed.
        """
        s = str(c) if not isinstance(c, discord.Embed) else json.dumps(c.to_dict())
        return await reddit_helper.get_item(self.reddit, self.subreddits, s)

    def get_reactions_embed(self, embed_color: discord.Color = None):
        """
        Load an embed with all the configured reactions per subreddit.

        Parameters
        ----------
        embed_color : discord.Color
            The color to be used for the embed, if not specified, the
            :attr:`~banhammer.Banhammer.embed_color` is used.

        Returns
        -------
        embed: discord.Embed
            The embed listing all the configured reactions per subreddit.
        """
        return self.message_builder.get_reactions_embed(self.subreddits)

    def get_subreddits_embed(self, embed_color: discord.Color = None):
        """
        Load an embed with all the configured subreddits and their enabled streams.

        Parameters
        ----------
        embed_color : discord.Color
            The color to be used for the embed, if not specified, the
            :attr:`~banhammer.Banhammer.embed_color` is used.

        Returns
        -------
        embed: discord.Embed
            The embed of all the subreddits and their enabled streams.
        """
        return self.message_builder.get_subreddits_embed(self.subreddits)

    def run(self):
        """
        Start the banhammer poll loop.
        """
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), "WELCOME.md"))
        with open(path) as f:
            print("")
            BOLD = '\033[1m'
            END = '\033[0m'
            print(re.sub(r"\*\*(.+)\*\*", r"{}\1{}".format(BOLD, END), f.read()))
            print("")

        if self.item_funcs or self.action_funcs:
            self.loop.create_task(self.send_items())
