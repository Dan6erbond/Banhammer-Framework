import logging
import re
from urllib.parse import urlparse

import apraw

from ..models import RedditItem

URL_PATTERN = re.compile(r"((https:\/\/)?((www|old|np|mod)\.)?(reddit|redd){1}(\.com|\.it){1}([a-zA-Z0-9\/_]+))")
logger = logging.getLogger("banhammer")


async def get_item(reddit: apraw.Reddit, subreddits, str):
    for u in URL_PATTERN.findall(str):
        if is_url(u[0]):
            item = await get_item_from_url(reddit, subreddits, u[0])
            if item:
                return item
            else:
                continue
    return None


async def get_item_from_url(reddit: apraw.Reddit, subreddits, url):
    if url.startswith("https://mod.reddit.com/mail/all/"):
        id = url.split("/")[-1] if url.split("/")[-1] != "" else url.split("/")[-2]

        for subreddit in subreddits:
            try:
                modmail = await subreddit._subreddit.modmail(id)
                if hasattr(modmail, "subject"):
                    return RedditItem(modmail, subreddit, "url")
            except Exception as e:
                logger.error(e)

        return None

    item = None
    try:
        item = await reddit.comment(url=url)
    except Exception as e:
        logger.error(e)
        try:
            item = await reddit.submission(url=url)
        except Exception as e:
            logger.error(e)
            return None

    item_subreddit = await item.subreddit()

    subreddit = None
    for sub in subreddits:
        s = await sub.get_subreddit()
        if s.id == item_subreddit.id:
            subreddit = sub
            break

    if subreddit:
        return RedditItem(item, subreddit, "url")


def is_url(url):
    check = urlparse(url)
    return check.scheme != "" and check.netloc != ""
