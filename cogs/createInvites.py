import discord
from discord.abc import GuildChannel
from discord.ext import commands

from discord import ApplicationContext, TextChannel, SlashCommandOptionType


class InviteCommand(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.slash_command(
        name="create-invite",
        description="Creates an invite that never expires in the given channel and sends it to a given channel"
    )
    @discord.option(
        input_type=SlashCommandOptionType.channel,
        name="invite_channel",
        description="The channel, where the invite gets created",
        required=False
    )
    @discord.default_permissions(administrator=True)
    async def create_invite(
            self,
            ctx: ApplicationContext,
            invite_channel: GuildChannel = None
    ):
        await ctx.defer(ephermal=True)

        invite_channel = invite_channel or ctx.channel

        try:
            invite_link = await invite_channel.create_invite(
                reason=f"Command by {ctx.author}",
                max_age=0,
                max_uses=0,
                unique=True
            )
        except discord.HTTPException as e:
            print(f"Error while creating an invite: {e}")
            await ctx.edit(content=f"An error occurred while creating the invite.")
            return

        await ctx.respond(
            embed=discord.Embed(
                title="Invite link",
                description=f"- Invite: [discord.gg/{invite_link.code}](https://discord.gg/{invite_link.code})`\n- Channel: {invite_channel.mention}",
            )
        )


def setup(bot):
    bot.add_cog(InviteCommand(bot))
