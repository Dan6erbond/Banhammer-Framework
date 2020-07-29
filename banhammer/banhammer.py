import asyncio
import json
import os
import re
from typing import Awaitable, Callable, Dict, Tuple, Union

import apraw
import discord
from apraw.utils import ExponentialCounter

from .const import BANHAMMER_PURPLE, logger
from .models import (EventFilter, EventHandler, GeneratorIdentifier,
                     ItemAttribute, MessageBuilder, ReactionHandler,
                     RedditItem, Subreddit)
from .utils import reddit_helper


class Banhammer:
    """
    The main Banhammer class that manages the event loop to poll Reddit and forward items to configured callables.
    """

    def __init__(self, reddit: apraw.Reddit, counter: ExponentialCounter = ExponentialCounter(16), bot: discord.Client = None, embed_color: discord.Colour = BANHAMMER_PURPLE,
                 change_presence: bool = False, message_builder: MessageBuilder = MessageBuilder(), reaction_handler: ReactionHandler = ReactionHandler()):
        """
        Create a Banhammer instance.

        Parameters
        ----------
        reddit : apraw.Reddit
            The Reddit instance with which Subreddits are constructed and requests are made.
        counter : ExponentialCounter, optional
            The counter to use to increase/decrease wait times based on whether items were found.
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
        self.message_builder = message_builder
        self.reaction_handler = reaction_handler
        self.embed_color = embed_color

        self._bot = bot
        self._change_presence = change_presence
        self._counter = counter

        self.subreddits = list()

        self._event_handlers = list()
        self._loop = asyncio.get_event_loop()

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
            self.add_new_handler(func, **kwargs)
            return func

        return assign

    def add_new_handler(self, func: Callable[[RedditItem], Awaitable[None]], **kwargs):
        """
        Add a function to handle new posts.

        Parameters
        ----------
        func : Callable[[RedditItem], Awaitable[None]]
            The function that will be called when new posts are made.
        subreddit : str or Subreddit
            The subreddit to poll with this function.
        """
        self.add_event_handler(func, GeneratorIdentifier.NEW, **kwargs)

    async def handle_new(self, item: RedditItem):
        """
        Handle Reddit items from the new queues.

        The default implementation of this method calls the appropriate handlers that were
        assigned using Banhammer's decorators. If overriden, it is recommended to make a
        ``super()`` call, otherwise handlers may be missed.

        Parameters
        ----------
        item : RedditItem
            The item to forward to handlers.
        """
        for handler in self._event_handlers:
            await handler(item, GeneratorIdentifier.NEW)

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
            self.add_comments_handler(func, **kwargs)
            return func

        return assign

    def add_comments_handler(self, func: Callable[[RedditItem], Awaitable[None]], **kwargs):
        """
        Add a function to handle comments.

        Parameters
        ----------
        func : Callable[[RedditItem], Awaitable[None]]
            The function that will be called when comments are made.
        subreddit : str or Subreddit
            The subreddit to poll with this function.
        """
        self.add_event_handler(func, GeneratorIdentifier.COMMENTS, **kwargs)

    async def handle_comments(self, item: RedditItem):
        """
        Handle Reddit items from the comment queues.

        The default implementation of this method calls the appropriate handlers that were
        assigned using Banhammer's decorators. If overriden, it is recommended to make a
        ``super()`` call, otherwise handlers may be missed.

        Parameters
        ----------
        item : RedditItem
            The item to forward to handlers.
        """
        for handler in self._event_handlers:
            await handler(item, GeneratorIdentifier.COMMENTS)

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
            self.add_mail_handler(func, **kwargs)
            return func

        return assign

    def add_mail_handler(self, func: Callable[[RedditItem], Awaitable[None]], **kwargs):
        """
        Add a function to handle modmail.

        Parameters
        ----------
        func : Callable[[RedditItem], Awaitable[None]]
            The function that will be called when modmail are made.
        subreddit : str or Subreddit
            The subreddit to poll with this function.
        """
        self.add_event_handler(func, GeneratorIdentifier.MAIL, **kwargs)

    async def handle_mail(self, item: RedditItem):
        """
        Handle Reddit items from the mail queues.

        The default implementation of this method calls the appropriate handlers that were
        assigned using Banhammer's decorators. If overriden, it is recommended to make a
        ``super()`` call, otherwise handlers may be missed.

        Parameters
        ----------
        item : RedditItem
            The item to forward to handlers.
        """
        for handler in self._event_handlers:
            await handler(item, GeneratorIdentifier.MAIL)

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
            self.add_queue_handler(func, **kwargs)
            return func

        return assign

    def add_queue_handler(self, func: Callable[[RedditItem], Awaitable[None]], **kwargs):
        """
        Add a function to handle unmoderated posts.

        Parameters
        ----------
        func : Callable[[RedditItem], Awaitable[None]]
            The function that will be called when unmoderated posts are made.
        subreddit : str or Subreddit
            The subreddit to poll with this function.
        """
        self.add_event_handler(func, GeneratorIdentifier.QUEUE, **kwargs)

    async def handle_queue(self, item: RedditItem):
        """
        Handle Reddit items from the modqueue.

        The default implementation of this method calls the appropriate handlers that were
        assigned using Banhammer's decorators. If overriden, it is recommended to make a
        ``super()`` call, otherwise handlers may be missed.

        Parameters
        ----------
        item : RedditItem
            The item to forward to handlers.
        """
        for handler in self._event_handlers:
            await handler(item, GeneratorIdentifier.QUEUE)

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
            self.add_reports_handler(func, **kwargs)
            return func

        return assign

    def add_reports_handler(self, func: Callable[[RedditItem], Awaitable[None]], **kwargs):
        """
        Add a function to handle reported posts.

        Parameters
        ----------
        func : Callable[[RedditItem], Awaitable[None]]
            The function that will be called when reported posts are made.
        subreddit : str or Subreddit
            The subreddit to poll with this function.
        """
        self.add_event_handler(func, GeneratorIdentifier.REPORTS, **kwargs)

    async def handle_reports(self, item: RedditItem):
        """
        Handle Reddit items from the reports queue.

        The default implementation of this method calls the appropriate handlers that were
        assigned using Banhammer's decorators. If overriden, it is recommended to make a
        ``super()`` call, otherwise handlers may be missed.

        Parameters
        ----------
        item : RedditItem
            The item to forward to handlers.
        """
        for handler in self._event_handlers:
            await handler(item, GeneratorIdentifier.REPORTS)

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
            self.add_mod_actions_handler(func, *args, **kwargs)
            return func

        return assign

    def add_mod_actions_handler(self, func: Callable[[RedditItem], Awaitable[None]], *args, **kwargs):
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
        self.add_event_handler(
            func,
            GeneratorIdentifier.MOD_ACTIONS,
            EventFilter(ItemAttribute.MOD, *(mod for mod in kwargs.get("mods", tuple())), *args),
            **kwargs)

    async def handle_mod_actions(self, item: RedditItem):
        """
        Handle Reddit items from the mod action queues.

        The default implementation of this method calls the appropriate handlers that were
        assigned using Banhammer's decorators. If overriden, it is recommended to make a
        ``super()`` call, otherwise handlers may be missed.

        Parameters
        ----------
        item : RedditItem
            The item to forward to handlers.
        """
        for handler in self._event_handlers:
            await handler(item, GeneratorIdentifier.MOD_ACTIONS)

    def add_event_handler(self, func: Callable[[RedditItem], Awaitable[None]],
                          identifier: GeneratorIdentifier, *args, **kwargs):
        """
        Add a function to handle the items from a specific generator in the
        :class:`~banhammer.models.Subreddit` class.

        Parameters
        ----------
        func : Callable[[RedditItem], Awaitable[None]]
            The function that will be called when items are retrieved.
        identifier : GeneratorIdentifier
            The identifier used to retrieve the subreddit's generator as well as the internal handler.
        subreddit : str or Subreddit
            The subreddit to poll with this function.
        """
        if asyncio.iscoroutinefunction(func):
            if kwargs.get("subreddit", None):
                if isinstance(kwargs["subreddit"], (str, apraw.models.Subreddit, Subreddit)):
                    args = (*args, EventFilter(ItemAttribute.SUBREDDIT, str(kwargs["subreddit"])))
                else:
                    args = (*args, EventFilter(ItemAttribute.SUBREDDIT, *(sub for sub in kwargs["subreddit"])))

            self._event_handlers.append(EventHandler(func, identifier, *args))

    async def send_items(self):
        """
        Start the loop to poll Reddit and send items.
        """
        while True:
            if self._bot and self._change_presence:
                try:
                    watching = discord.Activity(type=discord.ActivityType.watching, name="Reddit")
                    await self._bot.change_presence(activity=watching)
                except Exception as e:
                    logger.error(f"Failed to change bot presence: {e}")

            funcs = set()

            for handler in self._event_handlers:
                funcs.update((func, handler._identifier) for func in handler.get_sub_funcs(self.subreddits))

            found = False
            for func in funcs:
                async for item in func[0]():
                    found = True
                    await getattr(self, f"handle_{func[1]}")(item)

            if self._bot is not None and self._change_presence:
                try:
                    await self._bot.change_presence(activity=None)
                except Exception as e:
                    logger.error(f"Failed to change bot presence: {e}")

            wait_time = (found and self._counter.reset()) or self._counter.count()

            await asyncio.sleep(wait_time)

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

    def get_reactions_embed(self, *args, **kwargs):
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
        return self.message_builder.get_reactions_embed(self.subreddits, *args, **kwargs)

    def get_subreddits_embed(self, *args, **kwargs):
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
        return self.message_builder.get_subreddits_embed(self.subreddits, *args, **kwargs)

    def start(self):
        """
        Add the Banhammer poll loop to the ``asyncio`` event loop.
        """
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), "WELCOME.md"))
        with open(path) as f:
            print("")
            BOLD = '\033[1m'
            END = '\033[0m'
            print(re.sub(r"\*\*(.+)\*\*", r"{}\1{}".format(BOLD, END), f.read()))
            print("")

        self._loop.create_task(self.send_items())
