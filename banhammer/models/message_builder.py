import discord

from ..const import BOT_DISCLAIMER
from .item import RedditItem


class MessageBuilder:

    async def get_item_message(self, item: RedditItem):
        if item.type in ["submission", "comment"]:
            author_name = discord.utils.escape_markdown(await item.get_author_name())
            subreddit = discord.utils.escape_markdown(item.subreddit)
            return f"New {item.type} on /r/{subreddit} by /u/{author_name}!\n\n" + \
                f"{item.url}\n\n" + \
                f"**Title:** {item.item.title}\n**Body:**\n{item.body}"
        elif item.type == "modmail":
            author_name = discord.utils.escape_markdown(await item.get_author_name())
            subreddit = discord.utils.escape_markdown(item.subreddit)
            subject = discord.utils.escape_markdown(item.item.conversation.subject)
            return f"New message in modmail conversation '{subject}' on /r/{subreddit} by /u/{author_name}!" + \
                f"\n\n{item.body}"
        else:
            author_name = discord.utils.escape_markdown(await item.get_author_name())
            subreddit = discord.utils.escape_markdown(item.subreddit)
            return f"New action taken by /u/{author_name} on /r/{subreddit}: `{item.body}`"

    async def get_item_embed(self, item: RedditItem, embed_color: discord.Color = None):
        embed = discord.Embed(
            colour=embed_color or item.subreddit.banhammer.embed_color
        )

        title = ""
        if item.type in ["submission", "comment"]:
            author_name = discord.utils.escape_markdown(await item.get_author_name())
            subreddit = discord.utils.escape_markdown(item.subreddit)
            if item.source == "reports":
                title = f"{item.type.title()} reported on /r/{subreddit} by /u/{author_name}!"
            else:
                title = f"New {item.type} on /r/{subreddit} by /u/{author_name}!"
        elif item.type == "modmail":
            author_name = discord.utils.escape_markdown(await item.get_author_name())
            subreddit = discord.utils.escape_markdown(item.subreddit)
            subject = discord.utils.escape_markdown(item.item.conversation.subject)
            title = f"New message in modmail conversation '{subject}' on /r/{subreddit} by /u/{author_name}!"
        else:
            author_name = discord.utils.escape_markdown(item.item._data['mod'])
            subreddit = discord.utils.escape_markdown(item.subreddit)
            title = f"New action taken by /u/{author_name} on /r/{subreddit}!"

        url = item.url
        embed.set_author(name=title, url=url if url else discord.Embed.Empty)

        if item.type == "submission":
            embed.add_field(
                name="Title",
                value=discord.utils.escape_markdown(item.item.title),
                inline=False)
            if item.item.is_self:
                embed.add_field(name="Body", value=item.body, inline=False)
            else:
                embed.add_field(
                    name="URL",
                    value=discord.utils.escape_markdown(item.item.url),
                    inline=False)
            if item.source == "reports":
                embed.add_field(
                    name="Reports",
                    value="\n".join(f"{r[1]} {r[0]}" for r in item.item.user_reports),
                    inline=False)
        elif item.type == "comment":
            embed.description = item.body
        elif item.type == "modmail":
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
