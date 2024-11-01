import discord
from discord import ApplicationContext
from discord.ext import commands
from discord.commands import slash_command, SlashCommandGroup

class StatusUpdates(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    createGroup = SlashCommandGroup(
        "create", desc
    )

	@slash_command(
        base_name="status",
        base_desription="Manage Status Incidents"
    )

def setup(bot):
    bot.bot.add_cog(StatusUpdates)