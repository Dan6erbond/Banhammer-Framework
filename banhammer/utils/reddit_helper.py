import re
from urllib.parse import urlparse

import apraw

from ..const import logger
from ..models import RedditItem

REDDIT_URL_PATTERN = re.compile(
    r"((https:\/\/)?((www|old|np|mod)\.)?(reddit|redd){1}(\.com|\.it){1}([a-zA-Z0-9\/_]+))")
POST_URL_PATTERN = re.compile(
    r"/r(?:/(?P<subreddit>\w+))/comments(?:/(?P<submission>\w+))(?:/\w+/(?P<comment>\w+))?")
MODMAIL_URL_PATTERN = re.compile(
    r"https://mod.reddit.com/mail/all/(?P<id>\w+)")


async def get_item(reddit: apraw.Reddit, subreddits, str):
    for u in REDDIT_URL_PATTERN.findall(str):
        if is_url(u[0]):
            item = await get_item_from_url(reddit, subreddits, u[0])
            if item:
                return item
            else:
                continue
    return None


async def get_item_from_url(reddit: apraw.Reddit, subreddits, url):
    match = MODMAIL_URL_PATTERN.search(url)
    if match:
        for subreddit in subreddits:
            try:
                modmail = await subreddit._subreddit.modmail(match.group("id"))
                if hasattr(modmail, "subject"):
                    return RedditItem(modmail, subreddit, "url")
            except Exception as e:
                logger.error(f"Failed to fetch modmail by ID '{match.group('id')}': {e}")
        return None

    match = POST_URL_PATTERN.search(url)
    if match and not match.group("comment"):
        try:
            item = await reddit.submission(match.group("submission"))
        except Exception as e:
            logger.error(f"Failed to fetch submission by ID '{match.group('submission')}': {e}")
            return None
    elif match:
        try:
            item = await reddit.comment(match.group("comment"))
        except Exception as e:
            logger.error(f"Failed to fetch comment by ID '{match.group('comment')}': {e}")
            return None
    else:
        return None

    try:
        item_subreddit = await item.subreddit()
    except Exception as e:
        logger.error(f"Failed to retrieve item {item} subreddit: {e}")
        return None
    else:
        for sub in subreddits:
            s = await sub.get_subreddit()
            if s.id == item_subreddit.id:
                return RedditItem(item, sub, "url")
    return None


def is_url(url):
    check = urlparse(url)
    return check.scheme != "" and check.netloc != ""
