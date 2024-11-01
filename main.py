import discord
import os
from dotenv import load_dotenv

from discord import InteractionContextType, IntegrationType

intents = discord.Intents.default()

bot = discord.Bot(
    intents=intents,
    # Stupid pycord deletes and recreates commands on every start | This can be switched off after the first start
    # Might switch to d.py in the future if it gets to annonying
    auto_sync_commands=True,
    default_command_contexts=[InteractionContextType.guild],
    default_command_integration_types=[IntegrationType.guild_install],
)


@bot.event
async def on_ready():
    print(f"{bot.user} ist online")


if __name__ == "__main__":
    for filename in os.listdir("cogs"):
        if filename.endswith(".py"):
            bot.load_extension(f"cogs.{filename.removesuffix('.py')}")

    load_dotenv()
    bot.run(os.getenv("botToken"))
