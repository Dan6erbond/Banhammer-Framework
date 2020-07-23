import json

import praw

import banhammer


class CustomPayload(banhammer.ReactionPayload):
    async def get_message(self):
        return "I handled the submission '{0.title}' from /r/{0.subreddit}.".format(self.item.item)


class CustomHandler(banhammer.ReactionHandler):
    def handle(self, reaction, item, payload):
        payload.actions.append("test action")
        return payload


class CustomBuilder(banhammer.MessageBuilder):
    def get_item_message(self, item):
        return "Item title: {}".format(item.item.title)


def run():
    # doing something with JSON here so PyCharm doesn't remove the import
    json.dumps({"sub": "banhammerdmeo"})

    reddit = praw.Reddit("TBHB")

    bh = banhammer.Banhammer(reddit, message_builder=CustomBuilder())

    sub = banhammer.Subreddit(bh, subreddit="banhammerdemo")
    sub.ignore_old()
    bh.add_subreddits(sub)

    bh.run()
    # print(json.dumps(bh.get_reactions_embed().to_dict(), indent=4))

    url = "https://www.reddit.com/r/banhammerdemo/comments/c66rdl"
    item = bh.get_item(url)

    print()
    print(bh.message_builder.get_ban_message(item, 12))
    print()

    print(item)
    # print(json.dumps(item.get_embed().to_dict(), indent=4))
    print()
    print("Item removed:", item.removed)
    print("Item author removed:", item.is_author_removed())
    print()

    payload = item.get_reaction("✔").handle()
    print(payload)
    payload = item.get_reaction("✔").handle(CustomPayload("Ravi"))
    print(payload)


run()
