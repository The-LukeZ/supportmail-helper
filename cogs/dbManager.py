import aiosqlite
import asyncio
import datetime
from discord.ext import commands
from discord import Bot
from discord.utils import utcnow


class DBManager(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(5)

        async with aiosqlite.connect("./databases/statusUpdates.db") as dbs:
            await dbs.execute(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    description TEXT DEFAULT NULL,
                    msg_id TEXT DEFAULT NULL,
                    created_at TEXT,
                    resolved_at TEXT DEFAULT NULL
                );
                """
            )
            await dbs.execute(
                """
                CREATE TABLE IF NOT EXISTS status_updates (
                	status_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT,
                    status INTEGER DEFAULT 1,
                    content TEXT,
                    updated_at TEXT,
					FOREIGN KEY (incident_id) REFERENCES incidents(id)
                )
                """
            )
            # Statuses:
            # 0: Resolved
            # 1: Down
            # 2: Investigating
            # 3: Monitoring
            # 4: Maintenance

        print(f"[{utcnow().isoformat(' ')}] DB updated.")
        return


def setup(bot):
    bot.add_cog(DBManager(bot))
