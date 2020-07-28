from datetime import datetime

import discord
from apraw.models import ModmailConversation, ModmailMessage
from discord.utils import escape_markdown

from ..const import BOT_DISCLAIMER, logger
from .item import RedditItem
from .reaction import ReactionPayload


class MessageBuilder:

    async def get_item_message(self, item: RedditItem):
        if item.type in ["submission", "comment"]:
            author_name = escape_markdown(await item.get_author_name())
            subreddit = escape_markdown(str(item.subreddit))
            return f"New {item.type} on /r/{subreddit} by /u/{author_name}!\n\n" + \
                f"{item.url}\n\n" + \
                f"**Title:** {item.item.title}\n**Body:**\n{item.body}"
        elif item.type == "modmail":
            author_name = escape_markdown(await item.get_author_name())
            subreddit = escape_markdown(str(item.subreddit))
            subject = escape_markdown(item.item.conversation.subject)
            return f"New message in modmail conversation '{subject}' on /r/{subreddit} by /u/{author_name}!" + \
                f"\n\n{item.body}"
        else:
            author_name = escape_markdown(await item.get_author_name())
            subreddit = escape_markdown(str(item.subreddit))
            return f"New action taken by /u/{author_name} on /r/{subreddit}: `{item.body}`"

    async def get_item_embed(self, item: RedditItem, embed_color: discord.Color = None):
        embed = discord.Embed(
            colour=embed_color or item.subreddit.banhammer.embed_color
        )

        if isinstance(item.item, ModmailConversation):
            embed.timestamp = datetime.utcfromtimestamp(item.item.last_updated)
        elif isinstance(item.item, ModmailMessage):
            embed.timestamp = datetime.utcfromtimestamp(item.item.conversation.last_updated)
        else:
            embed.timestamp = item.item.created_utc

        if item.type in ["submission", "comment"]:
            if item.source == "reports":
                title = f"{item.type.title()} reported on /r/{item.subreddit} by /u/{await item.get_author_name()}!"
            else:
                title = f"New {item.type} on /r/{item.subreddit} by /u/{await item.get_author_name()}!"
        elif item.type == "modmail":
            title = f"New message in modmail conversation '{item.item.conversation.subject}' on /r/{item.subreddit} by /u/{await item.get_author_name()}!"
        else:
            title = f"New action taken by /u/{await item.get_author_name()} on /r/{item.subreddit}!"

        subreddit = await item.subreddit.get_subreddit()
        embed.set_author(name=title,
                         url=item.url or discord.Embed.Empty,
                         icon_url=subreddit.community_icon or discord.Embed.Empty)

        if item.type == "submission":
            embed.add_field(
                name="Title",
                value=escape_markdown(item.item.title),
                inline=False)

            if item.item.link_flair_text:
                embed.description = f"Flair: `{item.item.link_flair_text}`"

            if item.item.is_self:
                embed.add_field(name="Body", value=item.body, inline=False)
            elif "i.redd.it" in item.item.url or any(item.item.url.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif")):
                embed.set_image(url=item.item.url)
            elif not item.item._data.get("poll_data", None):
                embed.add_field(
                    name="URL",
                    value=escape_markdown(item.item.url),
                    inline=False)

            if item.item._data.get("poll_data", None):
                options = [
                    f"◽ {escape_markdown(option['text'])}" for option in item.item.poll_data["options"]]
                embed.add_field(name="Poll", value="\n".join(options), inline=False)
            elif item.item._data.get("media_metadata", None):
                for _, media in item.item.media_metadata.items():
                    if media["e"] == "Image":
                        added = False
                        if isinstance(media.get("s", None), dict) and "u" in media["s"]:
                            embed.set_image(url=media["s"]["u"])
                            added = True
                        elif isinstance(media.get("p", None), list):
                            try:
                                embed.set_image(url=media["p"][-1]["u"])
                                added = True
                            except BaseException:
                                logger.warning(f"Unexpected media metadata: {media}")
                        else:
                            logger.warning(f"Unexpected media metadata: {media}")

                        if added:
                            break

            if item.source == "reports":
                embed.add_field(
                    name="Reports",
                    value="\n".join(f"{r[1]} {r[0]}" for r in item.item.user_reports),
                    inline=False)
        elif item.type in ("comment", "modmail"):
            embed.description = item.body
        elif item.type == "mod action":
            embed.description = f"Action: `{item.body}`"

        return embed

    def get_ban_message(self, item: RedditItem, ban_duration: int):
        ban_type = "permanent" if not ban_duration else "temporary"
        disclaimer = BOT_DISCLAIMER.format(item.subreddit.get_contact_url())
        return f"Our moderator team has reviewed [this post]({item.url}) and decided to give you a {ban_type} ban. " \
               f"If you wish to appeal this ban, please respond to this message.\n\n{disclaimer}"

    def format_reply(self, item: RedditItem, reply: str):
        disclaimer = BOT_DISCLAIMER.format(item.subreddit.get_contact_url())
        return f"{reply}\n\n{disclaimer}"

    async def get_payload_message(self, payload: ReactionPayload):
        if not payload.actions:
            payload.actions.append("dismissed")

        user = escape_markdown(payload.user)
        author_name = escape_markdown(await payload.item.get_author_name())
        url = escape_markdown(payload.item.url)

        return f"**{payload.item.type.title()} {' and '.join(payload.actions)} by {user}!**\n\n" \
               f"{payload.item.type.title()} by /u/{author_name}:\n\n{url}"

    async def get_payload_embed(self, payload: ReactionPayload, embed_color: discord.Color = None):
        if not payload.actions:
            payload.actions.append("dismissed")

        embed = discord.Embed(
            colour=embed_color or payload.item.subreddit.banhammer.embed_color
        )

        embed.timestamp = datetime.utcnow()

        author_name = escape_markdown(await payload.item.get_author_name())

        embed.set_author(name=f"{payload.item.type.title()} {' and '.join(payload.actions)} by {payload.user}!")
        embed.description = f"[{payload.item.type.title()}]({payload.item.url}) by /u/{author_name}."

        return embed
