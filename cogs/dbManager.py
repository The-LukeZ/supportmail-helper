import aiosqlite, asyncio, datetime
from discord.ext import commands

class DBManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(5)
        await self.bot.wait_until_ready()

        async with aiosqlite.connect("./databases/statusUpdates.db") as dbs:
            await dbs.execute(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    description TEXT DEFAULT NULL,
                    msg_id TEXT,
                    created_at TEXT,
                    resolved_at TEXT DEFAULT NULL
                );
                """
            )
            await dbs.execute(
                """
                CREATE TABLE IF NOT EXISTS status_updates (
                	status_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id INTEGER,
                    status TEXT DEFAULT "Investigating",
                    updated_at TEXT,
					FOREIGN KEY (incident_id) REFERENCES incidents(id)
                )
                """
            )

        print(f"[{datetime.datetime(datetime.UTC).isoformat(' ')}] DB updated.")
        return


def setup(bot):
    bot.add_cog(bot)