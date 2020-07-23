import discord

from banhammer import reaction


class CustomReactionPayload(reaction.ReactionPayload):

    async def get_embed(self, embed_color=None):
        embed = discord.Embed(
            colour=embed_color or item.subreddit.banhammer.embed_color
        )

        embed.set_author(name=f"**{self.item.type.title()} {' and '.join(self.actions)} by {self.user}!**")

        embed.add_field(name=f"{self.item.type.title()} by /u/{await self.item.get_author_name()}",
                        value=self.item.get_url(), inline=False)

        return embed
