from typing import List, Optional, Union

from apraw.models import (Comment, ModmailConversation, ModmailMessage,
                          Submission)

from ..const import logger
from ..exceptions import NoItemGiven, NotEligibleItem
from ..utils import yaml
from .item import RedditItem


class ReactionPayload:

    def __init__(self, user: str = "Banhammer"):
        self.item = None
        self.user = user
        self.actions = list()
        self.approved = False
        self.reply = ""
        self.emoji = ""

    def feed(self, item: RedditItem, approved: bool, user: str = "", emoji: str = "", reply: str = ""):
        self.item = item
        self.approved = approved
        self.user = user or self.user
        self.emoji = emoji
        self.reply = reply

    async def get_message(self):
        if len(self.actions) == 0:
            self.actions.append("dismissed")
        return f"**{self.item.type.title()} {' and '.join(self.actions)} by {self.user}!**\n\n" \
               f"{self.item.type.title()} by /u/{await self.item.get_author_name()}:\n\n" \
               f"{self.item.url}"

    def __repr__(self):
        return f"<ReactionPayload item={self.item} approved={self.approved} actions={self.actions}>"


class ReactionHandler:

    async def handle(self, reaction: 'Reaction', item: RedditItem, payload: ReactionPayload):
        logger.info(f"Handling item: {item}")
        if isinstance(item.item, (ModmailConversation, ModmailMessage)):
            conversation = item.item.conversation if isinstance(item, ModmailMessage) else item.item
            if reaction.archive:
                await conversation.archive()
                logger.info("Archived modmail.")
                payload.actions.append("archived")
            if reaction.mute:
                await conversation.mute()
                logger.info("Muted modmail.")
                payload.actions.append("muted")
            if reaction.reply != "":
                await conversation.reply(reaction.reply)
                logger.info("Replied to modmail.")
                payload.actions.append("replied to")
            return payload

        if await item.is_author_removed():
            await item.item.mod.remove()
            payload.actions.append("removed")
            await item.item.mod.lock()
            payload.actions.append("locked")
            logger.info("Removed and locked submission of deleted user.")

            payload.feed(item, False, "Banhammer")
            return payload

        if reaction.approve:
            await item.item.mod.approve()
            logger.info("Approved item.")
            payload.actions.append("approved")
        else:
            await item.item.mod.remove()
            logger.info("Removed item.")
            payload.actions.append("removed")

        if reaction.lock or not reaction.approve:
            await item.item.mod.lock()
            logger.info("Locked item.")
            payload.actions.append("locked")
        elif item.item.locked:
            await item.item.mod.unlock()
            logger.info("Unlocked item.")
            payload.actions.append("unlocked")

        if isinstance(item.item, Submission):
            if reaction.flair:
                await item.item.mod.flair(text=reaction.flair)
                logger.info("Flaired item.")
                payload.actions.append("flaired")

            if reaction.mark_nsfw:
                await item.item.mod.nsfw()
                logger.info("Marked item as NSFW.")
                payload.actions.append("marked NSFW")

        if reaction.reply:
            reply = await item.item.reply(reaction.reply)
            logger.info("Replied to item.")
            if reaction.distinguish_reply:
                await reply.mod.distinguish(sticky=reaction.sticky_reply)
                logger.info("Distinguished reply.")
            payload.actions.append("replied to")

        if isinstance(reaction.ban, int):
            ban_message = item.subreddit.banhammer.message_builder.get_ban_message(item, reaction.ban)
            if reaction.ban == 0:
                subreddit = await item.item.subreddit()
                await subreddit.banned.add(item.item.author.name, ban_reason="Breaking Rules",
                                           ban_message=ban_message, note="Banhammer Ban")
                logger.info("Permanently banned author.")
                payload.actions.append("/u/" + item.item.author.name + " permanently banned")
            else:
                subreddit = await item.item.subreddit()
                await subreddit.banned.add(item.item.author.name, ban_reason="Breaking Rules",
                                           duration=reaction.ban, ban_message=ban_message,
                                           note="Banhammer Ban")
                logger.info(f"Banned author for {reaction.ban} day(s).")
                payload.actions.append(f"/u/{item.item.author.name} banned for {reaction.ban} day(s)")

        return payload


class Reaction:

    def __init__(self, **kwargs):
        self.config = kwargs

        self.emoji = kwargs["emoji"].strip()

        data = {
            "type": "",
            "flair": "",
            "approve": False,
            "mark_nsfw": False,
            "lock": False,
            "reply": "",
            "sticky_reply": True,
            "distinguish_reply": True,
            "ban": None,
            "archive": False,
            "mute": False,
            "min_votes": 1,
            **kwargs
        }

        data["distinguish_reply"] = data["distinguish_reply"] or data["sticky_reply"]

        for k, v in data.items():
            setattr(self, k, v)

    def __str__(self):
        return self.emoji

    def __repr__(self):
        str = self.emoji

        if self.type in ["submission", "comment", ""]:
            if self.type:
                str += " | " + self.type
            else:
                str += " | submissions + comments"
            if self.flair:
                str += " | flair: " + self.flair
            str += " | " + ("approve" if self.approve else "remove")
            if self.mark_nsfw:
                str += " | mark NSFW"
            if self.lock or not self.approve:
                str += " | lock"
            if self.ban is not None:
                str += " | " + ("permanent ban" if self.ban == 0 else f"{self.ban} day ban")
        if self.reply:
            str += " | reply"
        if self.min_votes:
            str += f" | min votes: {self.min_votes}"

        return str

    async def handle(self, item: RedditItem, payload: Optional[ReactionPayload] = None, user: str = ""):
        if not self.eligible(item.item):
            raise NotEligibleItem()

        payload = payload or ReactionPayload()

        logger.info(f"Received payload: {payload}")

        payload.feed(item, self.approve, user or payload.user, self.emoji, self.reply)

        return await item.subreddit.banhammer.reaction_handler.handle(self, item, payload)

    def eligible(self, item: Union[Submission, Comment, ModmailMessage, ModmailConversation]):
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


def get_reactions(yml: str):
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


def ignore_reactions(reactions: Reaction, remove: Union[List[str], Reaction]):
    emojis = set(str(remove) if isinstance(remove, (str, Reaction)) else str(i) for i in remove)
    reactions = [r for r in reactions if r.emoji not in emojis]
    return reactions
