import enum
from typing import TYPE_CHECKING, Any, Awaitable, Callable, List

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
        if self._attribute == ItemAttribute.MOD:
            if item.type != "mod action":
                return False
            mod_name = await item.get_author_name()
            if not any(mod_name.lower() == str(v).lower() for v in self._values):
                return False
            elif self._reverse:
                return False
        elif self._attribute == ItemAttribute.AUTHOR:
            author_name = await item.get_author_name()
            if not any(author_name.lower() == str(v).lower() for v in self._values):
                return False
            elif self._reverse:
                return False
        elif self._attribute == ItemAttribute.SUBREDDIT:
            if not any(str(item.subreddit).lower() == str(v).lower() for v in self._values):
                return False
            elif self._reverse:
                return False
        return True

    def is_subreddit_valid(self, subreddit: 'Subreddit'):
        return any(str(subreddit).lower() == str(v).lower() for v in self._values) or not self._values


class EventHandler:

    def __init__(self, callback: Callable[['RedditItem'], Awaitable[None]], identifier: GeneratorIdentifier, *args):
        self._callback = callback
        self._identifier = identifier
        self._filters = args

    async def __call__(self, item: 'RedditItem', identifier: GeneratorIdentifier):
        if identifier != self._identifier:
            return

        valid = True
        for f in self._filters:
            if not await f.is_item_valid(item):
                valid = False
                break

        if valid:
            await self._callback(item)

    def get_sub_funcs(self, subreddits: List['Subreddit']):
        for subreddit in subreddits:
            if all(f.is_subreddit_valid(subreddit) for f in self._filters):
                yield getattr(subreddit, f"get_{self._identifier}")
