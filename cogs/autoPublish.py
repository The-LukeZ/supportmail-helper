import discord
from discord.ext import commands

class AutoPublisher(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.includedChannels = []

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.channel.id in self.includedChannels:
            try: await msg.publish()
            except: pass

        return

def setup(bot):
    bot.add_cog(AutoPublisher)