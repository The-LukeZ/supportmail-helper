from datetime import datetime, timezone

import discord
import aiosqlite
import random
from discord import ApplicationContext, Embed, TextChannel, Permissions
from discord.ext import commands, tasks
from discord.utils import utcnow

from utils.enums import IncidentStatus
from utils.incidents import format_incident


class StatusUpdates(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        # self.statusChannelId = 1113896662914572368 # Prod
        self.statusChannelId = 1109804800092155935  # Test
        self.currentEditing = {}  # { user_id: { id: incident_id, until: datetime } } - 5 minutes to edit

    @tasks.loop(minutes=1)
    async def cleanup(self):
        now = utcnow()
        for [user_id, data] in self.currentEditing.items():
            if data["until"] < now:
                del self.currentEditing[user_id]
        return

    @commands.slash_command(
        name="create-incident",
        description="Create a new incident",
    )
    @discord.default_permissions(manage_guild=True)
    @discord.guild_only()
    @discord.commands.option(
        name="title",
        description="The title of the incident",
        input_type=str,
        required=True,
        max_length=200,
    )
    @discord.commands.option(
        name="description",
        description="The description of the incident",
        input_type=str,
        required=False,
        max_length=512,
    )
    @discord.commands.option(
        name="status",
        description="The status of the incident",
        input_type=str,
        required=False,
        choices=[
            discord.OptionChoice(
                name=IncidentStatus.Down.name, value=IncidentStatus.Down.name
            ),
            discord.OptionChoice(
                name=IncidentStatus.Investigating.name, value=IncidentStatus.Investigating.name
            ),
            discord.OptionChoice(
                name=IncidentStatus.Monitoring.name, value=IncidentStatus.Monitoring.name
            ),
            discord.OptionChoice(
                name=IncidentStatus.Maintenance.name, value=IncidentStatus.Maintenance.name
            ),
        ]
    )
    @discord.commands.option(
        name="ping",
        description="Whether to ping the role",
        input_type=bool,
    )
    async def create_incident(
            self,
            ctx: ApplicationContext,
            title: str,
            description: str = None,
            status=IncidentStatus.Investigating.name,
            ping=False
    ):
        await ctx.defer(ephemeral=True)
        nowTs = utcnow()
        iId = ''

        async with aiosqlite.connect("./databases/statusUpdates.db") as db:
            while True:
                iId = ''.join(random.choices(
                    "abcdefghijklmnopqrstuvwxyz0123456789", k=5))

                exists = await db.execute(
                    "SELECT * FROM incidents WHERE id = ?", (iId,)
                )
                if not (await exists.fetchone()):
                    break
                continue

            cols = ["id", "title"]
            args: list[str | int] = [iId, title]
            if description is not None:
                cols.append("description")
                args.append(description)

            cols.append("created_at")
            args.append(nowTs.isoformat())

            await db.execute_insert(
                f"INSERT INTO incidents ({', '.join(cols)}) VALUES ({', '.join(['?' for _ in cols])})",
                (*args,)
            )
            await db.commit()
            status_id = await db.execute_insert(
                "INSERT INTO status_updates (incident_id, status, updated_at) VALUES (?, ?, ?)",
                (iId, IncidentStatus[status].value, nowTs.isoformat())
            )

            await ctx.edit(
                embeds=[
                    Embed(
                        title="Incident Created",
                        description="Waiting for sending...",
                        color=discord.Color.blurple()
                    )
                ]
            )

            channel: TextChannel = ctx.guild.get_channel(self.statusChannelId) or await ctx.guild.fetch_channel(
                self.statusChannelId)

            logMessage = await channel.send(
                content='<@&1111912369371758676>' if ping else None,
                embed=format_incident(
                    {
                        "id": iId,
                        "title": title,
                        "description": description,
                        "updates": [
                            {
                                "status_id": status_id,
                                "status": IncidentStatus[status],
                                "content": None,
                                "updated_at": nowTs,
                            }
                        ],
                        "created_at": nowTs,
                        "updated_at": nowTs
                    }
                )
            )

            await db.execute(
                "UPDATE incidents SET msg_id = ? WHERE id = ?",
                (logMessage.id, iId)
            )
            await db.commit()

        await ctx.edit(
            embeds=[
                Embed(
                    title="Incident Created",
                    description=f">>> - ID: `{iId}`\n- [Jump to incident]({logMessage.jump_url})",
                    color=discord.Color.green()
                )
            ]
        )
        return


def setup(bot):
    bot.add_cog(StatusUpdates(bot))
