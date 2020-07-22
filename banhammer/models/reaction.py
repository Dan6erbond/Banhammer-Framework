from apraw.models import (Comment, ModmailConversation, ModmailMessage,
                          Submission)

from ..exceptions import NoItemGiven, NotEligibleItem
from ..utils import yaml
from .item import RedditItem


class ReactionPayload:

    def __init__(self, user="Banhammer"):
        self.item = None
        self.user = user
        self.actions = list()
        self.approved = False
        self.reply = ""
        self.emoji = ""

    def __str__(self):
        return self.get_message()

    def feed(self, item, approved, user="", emoji="", reply=""):
        self.item = item
        self.approved = approved
        if user != "":
            self.user = user
        self.reply = reply

    def get_message(self):
        if len(self.actions) == 0:
            self.actions.append("dismissed")
        return f"**{self.item.type.title()} {' and '.join(self.actions)} by {self.user}!**\n\n" \
               f"{self.item.type.title()} by /u/{self.item.get_author_name()}:\n\n" \
               f"{self.item.get_url()}"


class ReactionHandler:

    def handle(self, reaction, item, payload):
        return self.gen_handle(reaction, item, payload)

    def gen_handle(self, reaction, item, payload):
        if isinstance(item.item, (ModmailConversation, ModmailMessage)):
            conversation = item.item.conversation if isinstance(item, ModmailMessage) else item.item
            if reaction.archive:
                conversation.archive()
                payload.actions.append("archived")
            if reaction.mute:
                conversation.mute()
                payload.actions.append("muted")
            if reaction.reply != "":
                conversation.reply(reaction.reply)
                payload.actions.append("replied to")
            return payload

        is_submission = isinstance(item.item, Submission)
        is_comment = isinstance(item.item, Comment)

        if item.is_removed() or item.is_author_removed():
            item.item.mod.remove()
            payload.actions.append("removed")
            item.item.mod.lock()
            payload.actions.append("locked")

            payload.feed(item, False, "Banhammer")
            return payload

        if reaction.approve:
            item.item.mod.approve()
            payload.actions.append("approved")
        else:
            item.item.mod.remove()
            payload.actions.append("removed")

        if reaction.lock or not reaction.approve:
            item.item.mod.lock()
            payload.actions.append("locked")
        else:
            item.item.mod.unlock()

        if is_submission:
            if reaction.flair != "":
                item.item.mod.flair(text=reaction.flair)
                payload.actions.append("flaired")

            if reaction.mark_nsfw:
                item.item.mod.nsfw()
                payload.actions.append("marked NSFW")

        if reaction.reply != "":
            reply = item.item.reply(reaction.reply)
            if reaction.distinguish_reply:
                reply.mod.distinguish(sticky=reaction.sticky_reply)
            payload.actions.append("replied to")

        if isinstance(reaction.ban, int):
            ban_message = item.subreddit.banhammer.message_builder.get_ban_message(item, reaction.ban)
            if reaction.ban == 0:
                item.item.subreddit.banned.add(item.item.author.name, ban_reason="Breaking Rules",
                                               ban_message=ban_message, note="Banhammer Ban")
                payload.actions.append("/u/" + item.item.author.name + " permanently banned")
            else:
                item.item.subreddit.banned.add(item.item.author.name, ban_reason="Breaking Rules",
                                               duration=reaction.ban, ban_message=ban_message,
                                               note="Banhammer Ban")
                payload.actions.append(f"/u/{item.item.author.name} banned for {reaction.ban} day(s)")

        return payload


class Reaction:

    def __init__(self, **kwargs):
        self.config = kwargs

        self.emoji = kwargs["emoji"] if "emoji" in kwargs else ""
        self.emoji = self.emoji.strip()

        self.type = kwargs["type"] if "type" in kwargs else ""
        self.flair = kwargs["flair"] if "flair" in kwargs else ""
        self.approve = kwargs["approve"] if "approve" in kwargs else False
        self.mark_nsfw = kwargs["mark_nsfw"] if "mark_nsfw" in kwargs else False
        self.lock = kwargs["lock"] if "lock" in kwargs else False
        self.reply = kwargs["reply"] if "reply" in kwargs else ""

        self.distinguish_reply = kwargs["distinguish_reply"] if "distinguish_reply" in kwargs else True
        self.sticky_reply = kwargs["sticky_reply"] if "sticky_reply" in kwargs else True
        if self.sticky_reply:
            self.distinguish_reply = True

        self.ban = kwargs["ban"] if "ban" in kwargs else None
        self.archive = kwargs["archive"] if "archive" in kwargs else False
        self.mute = kwargs["mute"] if "mute" in kwargs else False
        self.min_votes = kwargs["min_votes"] if "min_votes" in kwargs else 1

        self.item = None

    def __str__(self):
        str = self.emoji

        if self.type in ["submission", "comment", ""]:
            if self.type != "":
                str += " | " + self.type
            else:
                str += " | submissions + comments"
            if self.flair != "":
                str += " | flair: " + self.flair
            str += " | " + ("approve" if self.approve else "remove")
            if self.mark_nsfw:
                str += " | mark NSFW"
            if self.lock or not self.approve:
                str += " | lock"
            if self.ban is not None:
                str += " | " + ("permanent ban" if self.ban == 0 else f"{self.ban} day ban")
        if self.reply != "":
            str += " | reply"
        if self.min_votes:
            str += f" | min votes: {self.min_votes}"

        return str

    def handle(self, payload=ReactionPayload(), user="", item=None):
        if item is None and self.item is not None:
            item = self.item

        if not isinstance(item, RedditItem) or item is None:
            raise NoItemGiven()

        if not self.eligible(item.item):
            raise NotEligibleItem()

        user = payload.user if user == "" else user

        payload.feed(item, self.approve, user, self.emoji, self.reply)

        return item.subreddit.banhammer.reaction_handler.handle(self, item, payload)

    def eligible(self, item):
        if isinstance(item, Submission):
            if self.type == "" or self.type == "submission":
                return True
        elif isinstance(item, Comment):
            if self.type == "" or self.type == "comment":
                return True
        elif isinstance(item, (ModmailMessage, ModmailConversation)):
            if self.type == "mail":
                return True
        return False


def get_reactions(yml):
    result = yaml.get_list(yml)
    ignore = list()
    emojis = set()
    for item in result:
        if "ignore" in item:
            ignore = [i.strip() for i in item["ignore"].split(",")]
            result.remove(item)
            break
    reactions = result
    reactions = [Reaction(**r) for r in result if "emoji" in r]
    return {
        "ignore": ignore,
        "reactions": reactions
    }


def ignore_reactions(reactions, remove):
    emojis = set(i.emoji if isinstance(item, Reaction) else i for i in remove)
    reactions = [r for r in reactions if react.emoji not in emojis]
    return reactions
