from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.subreddit import Subreddit


class BanhammerException(Exception):
    def __init__(self, msg: str):
        self.msg = msg

    def __str__(self):
        return str(self.msg)


class NotModerator(BanhammerException):
    def __init__(self, user: str, sub: 'Subreddit'):
        super().__init__(f"/u/{user} doesn't moderate /r/{sub}.")


class NoRedditInstance(BanhammerException):
    def __init__(self):
        super().__init__("No <apraw.Reddit> instance was given to the <banhammer.Subreddit> object.")


class NoItemGiven(BanhammerException):
    def __init__(self):
        super().__init__("No <banhammer.RedditItem> was given to the <banhammer.Reaction> instance.")


class NotEligibleItem(BanhammerException):
    def __init__(self):
        super().__init__("The <banhammer.RedditItem> given to the <banhammer.Reaction> object cannot be handled.")
