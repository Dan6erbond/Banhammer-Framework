import asyncio
import enum
from typing import TYPE_CHECKING, Any, Awaitable, Callable, List, Union

if TYPE_CHECKING:
    from .item import RedditItem
    from .subreddit import Subreddit


class ItemAttribute(enum.Enum):
    SUBREDDIT = "subreddit"
    AUTHOR = "author"
    MOD = "mod"


class GeneratorIdentifier(enum.Enum):
    NEW = "new"
    COMMENTS = "comments"
    REPORTS = "reports"
    MAIL = "mail"
    QUEUE = "queue"
    MOD_ACTIONS = "mod_actions"

    def __str__(self):
        return str(self.value)


class EventFilter:

    def __init__(self, attribute: ItemAttribute, *args, **kwargs):
        self._attribute = attribute
        self._values = args
        self._reverse = kwargs.get("reverse", False)

    async def is_item_valid(self, item: 'RedditItem'):
        if not self._values:
            return True

        match = True

        if self._attribute == ItemAttribute.MOD:
            if item.type != "mod action":
                return False
            mod_name = await item.get_author_name()
            match = any(mod_name.lower() == str(v).lower() for v in self._values)
        elif self._attribute == ItemAttribute.AUTHOR:
            author_name = await item.get_author_name()
            match = any(author_name.lower() == str(v).lower() for v in self._values)
        elif self._attribute == ItemAttribute.SUBREDDIT:
            match = any(str(item.subreddit).lower() == str(v).lower() for v in self._values)

        return (not self._reverse and match) or (self._reverse and not match)

    def is_subreddit_valid(self, subreddit: 'Subreddit'):
        return self._attribute != ItemAttribute.SUBREDDIT or any(
            str(subreddit).lower() == str(v).lower() for v in self._values) or not self._values


class EventHandler:

    def __init__(self, callback: Callable[['RedditItem'], Awaitable[None]], identifier: GeneratorIdentifier, *args):
        self._callback = callback
        self._identifiers = {identifier}
        self._filters = list(args)
        self._takes_self = False

    @classmethod
    def new(cls, **kwargs):
        def wrapper(func: Callable[['RedditItem'], Awaitable[None]]):
            return cls.create_event_handler(func, GeneratorIdentifier.NEW, **kwargs)
        return wrapper

    @classmethod
    def comments(cls, **kwargs):
        def wrapper(func: Callable[['RedditItem'], Awaitable[None]]):
            return cls.create_event_handler(func, GeneratorIdentifier.COMMENTS, **kwargs)
        return wrapper

    @classmethod
    def mail(cls, **kwargs):
        def wrapper(func: Callable[['RedditItem'], Awaitable[None]]):
            return cls.create_event_handler(func, GeneratorIdentifier.MAIL, **kwargs)
        return wrapper

    @classmethod
    def queue(cls, **kwargs):
        def wrapper(func: Callable[['RedditItem'], Awaitable[None]]):
            return cls.create_event_handler(func, GeneratorIdentifier.QUEUE, **kwargs)
        return wrapper

    @classmethod
    def reports(cls, **kwargs):
        def wrapper(func: Callable[['RedditItem'], Awaitable[None]]):
            return cls.create_event_handler(func, GeneratorIdentifier.REPORTS, **kwargs)
        return wrapper

    @classmethod
    def mod_actions(cls, *args, **kwargs):
        def wrapper(func: Callable[['RedditItem'], Awaitable[None]]):
            event_filter = EventFilter(ItemAttribute.MOD, *kwargs.get("mods", tuple()), *args)
            create_args = (event_filter,) if event_filter._values else tuple()
            return cls.create_event_handler(func, GeneratorIdentifier.MOD_ACTIONS, *create_args, **kwargs)
        return wrapper

    @classmethod
    def create_event_handler(cls, handler: Union['EventHandler', Callable[['RedditItem'], Awaitable[None]]],
                             identifier: GeneratorIdentifier, *args, **kwargs):
        if not isinstance(handler, EventHandler) and not asyncio.iscoroutinefunction(handler):
            raise TypeError("Event handler must be a coroutine function or of type <banhammer.models.EventHandler>.")

        args = (*args, *getattr(handler, "_filters", tuple()))

        values = tuple(*kwargs.get("subreddits", tuple()), str(kwargs.get("subreddit", "")))
        if values:
            event_filter = EventFilter(ItemAttribute.SUBREDDIT, values)
            args = (*args, event_filter)

        if not isinstance(handler, EventHandler):
            handler = EventHandler(handler, identifier, *args)
        else:
            handler._identifiers.add(identifier)
            handler._filters.extend(args)

        return handler

    @classmethod
    def filter(cls, attribute: ItemAttribute, *args, **kwargs):
        def wrapper(handler: Union['EventHandler', Callable[['RedditItem'], Awaitable[None]]]):
            if not isinstance(handler, EventHandler) and not asyncio.iscoroutinefunction(handler):
                raise TypeError("Event handler must be a coroutine function or of type <banhammer.models.EventHandler>.")

            handler._filters = getattr(handler, "_filters", list())
            handler._filters.append(EventFilter(attribute, *args, **kwargs))
            return handler
        return wrapper

    async def __call__(self, identifier: GeneratorIdentifier, *args):
        valid = identifier in self._identifiers

        if not valid:
            return

        for f in self._filters:
            if not await f.is_item_valid(args[-1]):
                valid = False
                break

        if valid:
            await self._callback(*args)

    def get_sub_funcs(self, subreddits: List['Subreddit']):
        for subreddit in subreddits:
            if all(f.is_subreddit_valid(subreddit) for f in self._filters if f._attribute == ItemAttribute.SUBREDDIT):
                for identifier in self._identifiers:
                    yield getattr(subreddit, f"get_{identifier}"), identifier
