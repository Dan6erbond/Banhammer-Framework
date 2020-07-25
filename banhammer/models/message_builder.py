import discord

from ..const import BOT_DISCLAIMER
from .item import RedditItem


class MessageBuilder:
    async def get_item_message(self, item: RedditItem):
        if item.type in ["submission", "comment"]:
            return f"New {item.type} on /r/{item.item._data['subreddit']} by /u/{await item.get_author_name()}!\n\n" + \
                f"https://www.reddit.com{item.item.permalink}\n\n" + \
                f"**Title:** {item.item.title}\n**Body:**\n{item.item.selftext}"
        elif item.type == "modmail":
            return f"New message in modmail conversation '{item.item.conversation.subject}' on /r/{item.item.conversation._data['owner']} by /u/{await item.get_author_name()}!" + \
                f"\n\n{item.item.body_md}"
        else:
            return f"New action taken by /u/{item.item._data['mod']} on /r/{item.item.subreddit}: `{item.item.action}`"

    async def get_item_embed(self, item: RedditItem, embed_color: discord.Color = None):
        embed = discord.Embed(
            colour=embed_color or item.subreddit.banhammer.embed_color
        )

        title = ""
        if item.type in ["submission", "comment"]:
            if item.source == "reports":
                title = f"{item.type.title()} reported on /r/{item.item._data['subreddit']} by /u/{await item.get_author_name()}!"
            else:
                title = f"New {item.type} on /r/{item.item._data['subreddit']} by /u/{await item.get_author_name()}!"
        elif item.type == "modmail":
            title = f"New message in modmail conversation '{item.item.conversation.subject}' on /r/{item.item.conversation._data['owner']} by /u/{await item.get_author_name()}!"
        else:
            title = f"New action taken by /u/{item.item._data['mod']} on /r/{item.item._data['subreddit']}!"

        url = item.url
        embed.set_author(name=title, url=url if url else discord.Embed.Empty)

        if item.type == "submission":
            embed.add_field(name="Title", value=item.item.title, inline=False)
            if item.item.is_self:
                embed.add_field(name="Body",
                                value=item.item.selftext if item.item.selftext else "Empty",
                                inline=False)
            else:
                embed.add_field(name="URL", value=item.item.url, inline=False)
            if item.source == "reports":
                reports = [f"{r[1]} {r[0]}" for r in item.item.user_reports]
                embed.add_field(name="Reports", value="\n".join(reports), inline=False)
        elif item.type == "comment":
            embed.description = item.item.body
        elif item.type == "modmail":
            embed.description = item.item.body_md
        elif item.type == "mod action":
            embed.description = f"Action: `{item.item.action}`"

        return embed

    def get_ban_message(self, item, ban_duration):
        ban_type = "permanent" if not ban_duration else "temporary"
        disclaimer = BOT_DISCLAIMER.format(item.subreddit.get_contact_url())
        return f"Our moderator team has reviewed [this post]({item.url}) and decided to give you a {ban_type} ban. " \
               f"If you wish to appeal this ban, please respond to this message.\n\n{disclaimer}"
