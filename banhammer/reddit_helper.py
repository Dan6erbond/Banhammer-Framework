import re
from urllib.parse import urlparse

import apraw

from .item import RedditItem

URL_PATTERN = re.compile(r"((https:\/\/)?((www|old|np|mod)\.)?(reddit|redd){1}(\.com|\.it){1}([a-zA-Z0-9\/_]+))")


async def get_item(reddit: apraw.Reddit, subreddits, str):
    for u in URL_PATTERN.findall(str):
        if is_url(u[0]):
            item = get_item_from_url(reddit, subreddits, u[0])
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
                print("{}: {}".format(type(e), e))

        return None

    item = None
    try:
        item = await reddit.comment(url=url)
    except Exception:
        try:
            item = await reddit.submission(url=url)
        except Exception as e:
            print("Invalid URL:", e)
            return None

    try:
        if not hasattr(item, "subreddit"):  # truly verify if it's a reddit comment or submission
            return None
    except Exception:
        return None

    subreddit = None
    for sub in subreddits:
        if sub.subreddit.id == item.subreddit.id:
            subreddit = sub
            break

    return RedditItem(item, subreddit, "url")


def is_url(url):
    check = urlparse(url)
    return check.scheme != "" and check.netloc != ""
