from datetime import datetime
from typing import List

import discord
from apraw.models import ModmailConversation, ModmailMessage
from discord.utils import escape_markdown

from ..const import BANHAMMER_PURPLE, BOT_DISCLAIMER, logger
from .item import RedditItem
from .reaction import ReactionPayload
from .subreddit import Subreddit


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

    async def get_item_embed(self, item: RedditItem, embed_color: discord.Color = None,
                             embed_template: discord.Embed = None):
        embed = embed_template or discord.Embed(
            colour=embed_color or item.subreddit.banhammer.embed_color
        )

        if isinstance(item.item, ModmailConversation):
            try:
                embed.timestamp = datetime.utcfromtimestamp(item.item.last_updated)
            except Exception as e:
                logger.error(f"Error setting timestamp <{item.item.last_updated}>: {e}")
        elif isinstance(item.item, ModmailMessage):
            try:
                timestamp = int(float(item.item.conversation.last_updated))
                embed.timestamp = datetime.utcfromtimestamp(timestamp)
            except Exception as e:
                logger.error(f"Error converting timestamp <{item.item.conversation.last_updated}> to int: {e}")
        else:
            try:
                embed.timestamp = datetime.utcfromtimestamp(item.item._data["created_utc"])
            except Exception as e:
                logger.error(f"Error setting timestamp <{item.item._data['created_utc']}>: {e}")

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
            embed.add_field(name="Title", value=escape_markdown(item.item.title), inline=False)

            if item.item.link_flair_text:
                embed.description = f"Flair: `{item.item.link_flair_text}`"

            if item.item.is_self:
                embed.add_field(name="Body", value=item.body, inline=False)
            elif "i.redd.it" in item.item.url or any(item.item.url.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif")):
                embed.set_image(url=item.item.url)
            elif not item.item._data.get("poll_data", None):
                embed.add_field(name="URL", value=escape_markdown(item.item.url), inline=False)

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
                user_reports = "\n".join(f"{r[1]} {r[0]}" for r in item.item.user_reports)
                if user_reports:
                    embed.add_field(name="User Reports", value=user_reports, inline=False)

                mod_reports = "\n".join(f"{r[1]} {r[0]}" for r in item.item.mod_reports)
                if mod_reports:
                    embed.add_field(name="Mod Reports", value=mod_reports, inline=False)
        elif item.type in ("comment", "modmail"):
            embed.description = item.body
        elif item.type == "mod action":
            embed.description = f"Action: `{item.body}`"

        return embed

    def get_ban_message(self, item: RedditItem, ban_duration: int):
        ban_type = "permanent" if not ban_duration else "temporary"
        disclaimer = BOT_DISCLAIMER.format(item.subreddit.contact_url)
        return f"Our moderator team has reviewed [this post]({item.url}) and decided to give you a {ban_type} ban. " \
               f"If you wish to appeal this ban, please respond to this message.\n\n{disclaimer}"

    def format_reply(self, item: RedditItem, reply: str):
        disclaimer = BOT_DISCLAIMER.format(item.subreddit.contact_url)
        return f"{reply}\n\n{disclaimer}"

    async def get_payload_message(self, payload: ReactionPayload):
        if not payload.actions:
            payload.actions.append("dismissed")

        user = escape_markdown(payload.user)
        author_name = escape_markdown(await payload.item.get_author_name())
        url = escape_markdown(payload.item.url)

        return f"**{payload.item.type.title()} {' and '.join(payload.actions)} by {user}!**\n\n" \
               f"{payload.item.type.title()} by /u/{author_name}:\n\n{url}"

    async def get_payload_embed(self, payload: ReactionPayload, embed_color: discord.Color = None,
                                embed_template: discord.Embed = None):
        if not payload.actions:
            payload.actions.append("dismissed")

        embed = embed_template or discord.Embed(
            colour=embed_color or payload.item.subreddit.banhammer.embed_color
        )

        author_name = escape_markdown(await payload.item.get_author_name())

        embed.description = f"[{payload.item.type.title()}]({payload.item.url}) by /u/{author_name}."
        embed.timestamp = datetime.utcnow()

        embed.set_author(name=f"{payload.item.type.title()} {' and '.join(payload.actions)} by {payload.user}!")

        return embed

    def get_reactions_embed(self, subreddits: List[Subreddit], embed_color: discord.Color = None,
                            embed_template: discord.Embed = None):
        """
        Load an embed with all the configured reactions per subreddit.

        Parameters
        ----------
        subreddits : List[Subreddit]
            The subreddits to be included in the overview.
        embed_color : discord.Color
            The color to be used for the embed, if not specified, the
            :attr:`~banhammer.Banhammer.embed_color` is used.

        Returns
        -------
        embed: discord.Embed
            The embed listing all the configured reactions per subreddit.
        """
        embed = embed_template or discord.Embed(
            colour=embed_color or subreddits[0].banhammer.embed_color if subreddits else BANHAMMER_PURPLE
        )

        embed.title = "Configured reactions"
        embed.timestamp = datetime.utcnow()

        for sub in subreddits:
            embed.add_field(name="/r/" + str(sub),
                            value="\n".join([repr(r) for r in sub.reactions]),
                            inline=False)
        return embed

    def get_subreddits_embed(self, subreddits: List[Subreddit], embed_color: discord.Color = None,
                             embed_template: discord.Embed = None):
        """
        Load an embed with all the configured subreddits and their enabled streams.

        Parameters
        ----------
        subreddits : List[Subreddit]
            The subreddits to be included in the overview.
        embed_color : discord.Color
            The color to be used for the embed, if not specified, the
            :attr:`~banhammer.Banhammer.embed_color` is used.

        Returns
        -------
        embed: discord.Embed
            The embed of all the subreddits and their enabled streams.
        """
        embed = embed_template or discord.Embed(
            colour=embed_color or subreddits[0].banhammer.embed_color if subreddits else BANHAMMER_PURPLE
        )

        embed.title = "Subreddits' statuses"
        embed.description = "\n".join([s.status for s in subreddits])
        embed.timestamp = datetime.utcnow()

        return embed

    async def get_subreddit_reactions_embed(self, subreddit: Subreddit, embed_color: discord.Color = None,
                                            embed_template: discord.Embed = None):
        embed = embed_template or discord.Embed(
            colour=embed_color or subreddit.banhammer.embed_color
        )

        embed.timestamp = datetime.utcnow()

        sub = await subreddit.get_subreddit()
        embed.set_author(
            name=f"/r/{subreddit} Configured Reactions",
            url=f"https://www.reddit.com/r/{subreddit}/wiki/banhammer-reactions",
            icon_url=sub.community_icon or discord.Embed.Empty)

        fields = list()
        for reaction in subreddit.reactions:
            name = ' '.join(w.title() if w.islower() else w for w in reaction.__comments__.splitlines()
                            [0].replace('#', '', 1).strip().split()) if reaction.__comments__ else ""
            title = f"{name}: {reaction}" if name else f"`{reaction}`"
            text = repr(reaction).replace(str(reaction) + " | ", "")

            if reaction.reply:
                text.replace(" | reply", "")
                text += f"\n\n**Reply**\n>>> {reaction.reply.splitlines()[0]}"
                fields.append({"name": title, "value": text})
            else:
                fields = [{"name": title, "value": text}, *fields]
        for field in fields:
            embed.add_field(**field)

        return embed
