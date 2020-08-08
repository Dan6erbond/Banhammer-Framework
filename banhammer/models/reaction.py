from datetime import datetime
from typing import List, Optional, Union, Dict

import discord
from apraw.models import (Comment, ModmailConversation, ModmailMessage,
                          Submission)

from ..const import logger
from ..exceptions import NoItemGiven, NotEligibleItem
from ..utils import yaml
from .item import RedditItem


class ReactionPayload:

    def __init__(self, user: str = "Banhammer", item: RedditItem = None):
        self.user = user
        self.item = item
        self.actions = list()
        self.approved = False
        self.reply = ""
        self.emoji = ""
        self.performed_utc = datetime.utcnow()

    def feed(self, item: RedditItem, approved: bool, user: str = "", emoji: str = "", reply: str = ""):
        self.item = item
        self.approved = approved
        self.user = user or self.user
        self.emoji = emoji
        self.reply = reply

    async def get_message(self):
        return await self.item.subreddit.banhammer.message_builder.get_payload_message(self)

    async def get_embed(self, *args, **kwargs):
        return await self.item.subreddit.banhammer.message_builder.get_payload_embed(self, *args, **kwargs)

    def __repr__(self):
        return f"<ReactionPayload item={self.item} approved={self.approved} actions={self.actions}>"

    async def to_dict(self, convert_item=True, convert_datetime=False):
        return {
            "item": await self.item.to_dict() if convert_item else self.item,
            "user": self.user,
            "actions": self.actions,
            "approved": self.approved,
            "reply": self.reply,
            "emoji": self.emoji,
            "performed_utc": self.performed_utc.timestamp if convert_datetime else self.performed_utc
        }


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
                await conversation.reply(item.format_reply(reaction.reply))
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
            reply = await item.item.reply(item.format_reply(reaction.reply))
            logger.info("Replied to item.")
            if reaction.distinguish_reply:
                await reply.mod.distinguish(sticky=reaction.sticky_reply)
                logger.info("Distinguished reply.")
            payload.actions.append("replied to")

        if isinstance(reaction.ban, int):
            ban_message = item.get_ban_message(reaction.ban)
            author_name = await item.get_author_name()
            subreddit = await item.item.subreddit()
            if reaction.ban == 0:
                await subreddit.banned.add(author_name, ban_reason="Breaking Rules",
                                           ban_message=ban_message, note="Banhammer Ban")
                logger.info("Permanently banned author.")
                payload.actions.append(f"/u/ {author_name} permanently banned")
            else:
                await subreddit.banned.add(author_name, ban_reason="Breaking Rules",
                                           duration=reaction.ban, ban_message=ban_message,
                                           note="Banhammer Ban")
                logger.info(f"Banned author for {reaction.ban} day(s).")
                payload.actions.append(f"/u/{author_name} banned for {reaction.ban} day(s)")

        return payload


class Reaction:

    SCHEMA = {
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
        "min_votes": 1
    }

    def __init__(self, schema: Dict = None, **kwargs):
        self._schema = {**self.SCHEMA, **(schema or {})}

        self._data = {**self._schema, **kwargs}
        self._data["emoji"] = self._data["emoji"].strip()
        self._data["distinguish_reply"] = self._data["distinguish_reply"] or self._data["sticky_reply"]

        for k, v in self._data.items():
            if not hasattr(self, k):
                setattr(self, k, v)

    def copy(self) -> 'Reaction':
        return type(self)(self._schema, **self._data)

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
            if not self.type or self.type == "submission":
                return True
        elif isinstance(item, Comment):
            if not self.type or self.type == "comment":
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
