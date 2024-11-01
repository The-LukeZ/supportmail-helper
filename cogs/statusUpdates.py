from datetime import datetime, timezone

import discord
import aiosqlite
import random

from attr.validators import max_len
from discord import ApplicationContext, Embed, TextChannel, Permissions, SlashCommandGroup, PartialMessage, \
    AutocompleteContext, OptionChoice, message_command, Message, Interaction
from discord.ext import commands, tasks
from discord.utils import utcnow

from utils.enums import IncidentStatus
from utils.incidents import format_incident

command_status_choices = [
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


class StatusUpdates(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        # self.statusChannelId = 1113896662914572368 # Prod
        self.statusChannelId = 1109804800092155935  # Test
        # { user_id: { id: incident_id, until: datetime } } - 5 minutes to edit
        self.currentEditing = {}

    @tasks.loop(minutes=1)
    async def cleanup(self):
        now = utcnow()
        for [user_id, data] in self.currentEditing.items():
            if data["until"] < now:
                del self.currentEditing[user_id]
        return

    incident_group = SlashCommandGroup(
        name="incident",
        description="Incident management commands",
        default_member_permissions=Permissions(manage_guild=True)
    )

    @incident_group.command(
        name="create",
        description="Create a new incident",
    )
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
        description="The description of the initial status",
        input_type=str,
        required=False,
        max_length=512,
    )
    @discord.commands.option(
        name="status",
        description="The status of the incident",
        input_type=str,
        required=False,
        choices=command_status_choices
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
                        "updates": [
                            {
                                "status_id": status_id,
                                "status": IncidentStatus[status],
                                "content": description,
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

    async def get_active_incidents(self, ctx: AutocompleteContext) -> list[OptionChoice]:
        async with aiosqlite.connect("./databases/statusUpdates.db") as db:
            incidents = await db.execute(
                "SELECT id FROM incidents WHERE id NOT IN (SELECT DISTINCT incident_id FROM status_updates WHERE status != ?)",
                (IncidentStatus.Resolved.value,)
            )
            incidents = await incidents.fetchall()
            if not incidents or len(incidents) == 0:
                return [
                    OptionChoice(
                        name="No active incidents",
                        value="-none"
                    )
                ]
            return [
                OptionChoice(
                    name=incident[0],
                    value=incident[0]
                ) for incident in incidents
            ]

    @incident_group.command(
        name="update",
        description="Update an incident"
    )
    @discord.option(
        name="incident_id",
        description="The ID of the incident",
        input_type=str,
        required=True,
        autocomplete=get_active_incidents
    )
    @discord.option(
        name="status",
        description="The status of the update",
        input_type=str,
        required=True,
        choices=command_status_choices + [
            discord.OptionChoice(
                name=IncidentStatus.Resolved.name, value=IncidentStatus.Resolved.name
            )
        ]
    )
    @discord.option(
        name="description",
        description="A description for the status update",
        input_type=str,
        required=False,
        max_length=512
    )
    async def update_incident(
            self,
            ctx: ApplicationContext,
            incident_id: str,
            status: str,
            description: str = None
    ):
        await ctx.defer(ephemeral=True)

        if incident_id == "-none":
            await ctx.edit(
                content="Invalid Incident ID.",
            )
            return

        async with aiosqlite.connect("./databases/statusUpdates.db") as db:
            incidentRow = await db.execute(
                "SELECT id, title, msg_id FROM incidents WHERE id = ?", (
                    incident_id,)
            )
            incident = await incidentRow.fetchone()
            if not incident:
                await ctx.edit(
                    content="Incident not found",
                )
                return

            incident = {
                "id": incident[0],
                "title": incident[1],
                "msg_id": incident[2]
            }

            statusRows = await db.execute(
                "SELECT (status, content, updated_at) FROM status_updates WHERE incident_id = ? ORDER BY id DESC",
                (incident[0],)
            )
            statusRows = await statusRows.fetchone()

            if statusRows and statusRows[-1]["status"] == IncidentStatus.Resolved.value:
                await ctx.edit(
                    content="Incident is already resolved.",
                )
                return

            nowTs = utcnow()
            status_id = await db.execute_insert(
                "INSERT INTO status_updates (incident_id, status, content, updated_at) VALUES (?, ?, ?, ?)",
                (incident["id"], IncidentStatus[status].value,
                 description, nowTs.isoformat())
            )

            if status == IncidentStatus.Resolved.name:
                await db.execute(
                    "UPDATE incidents SET resolved_at = ? WHERE id = ?",
                    (nowTs.isoformat(), incident["id"])
                )
                await db.commit()

        channel: TextChannel = ctx.guild.get_channel(self.statusChannelId) or await ctx.guild.fetch_channel(
            self.statusChannelId)

        logMessage = PartialMessage(id=incident["msg_id"], channel=channel)

        updates = [
            {
                "status": IncidentStatus[update[0]],
                "content": update[1],
                "updated_at": datetime.fromisoformat(update[2])
            } for update in statusRows
        ]

        try:
            await logMessage.edit(
                embed=format_incident(
                    {
                        "id": incident["id"],
                        "title": incident["title"],
                        "updates":
                            [
                                {
                                    "status": IncidentStatus[update["status"]],
                                    "content": update["content"],
                                    "updated_at": datetime.fromisoformat(update["updated_at"])
                                } for update in updates
                        ]
                            +
                            [
                                {
                                    "status_id": status_id,
                                    "status": IncidentStatus[status],
                                    "content": description,
                                    "updated_at": nowTs,
                                }
                        ],
                        "created_at": incident["created_at"],
                        "updated_at": nowTs
                    }
                )
            )
        except discord.NotFound:
            await ctx.edit(
                content="Incident log message not found.",
            )
            return
        except Exception as e:
            await ctx.edit(
                content="An error occurred while updating the incident.",
                embeds=[{
                    "description": f"```{e}```"
                }]
            )
            return

        await ctx.edit(
            content="✅ | Incident updated.",
        )
        return

    @message_command(name="Resolve Incident")
    @discord.default_permissions(administrator=True)
    async def resolve_incident(self, ctx: ApplicationContext, message: Message):
        async with aiosqlite.connect("./databases/statusUpdates.db") as db:
            incidentRow = await db.execute(
                "SELECT id, title, msg_id, resolved_at FROM incidents WHERE msg_id = ?",
                (message.id,)
            )
            incident = await incidentRow.fetchone()

            if not incident:
                await ctx.respond(
                    content="Incident not found",
                    ephemeral=True
                )
                return

            if incident[3] is not None:
                await ctx.respond(
                    content="Incident is already resolved.",
                    ephemeral=True
                )
                return

            incident = {
                "id": incident[0],
                "title": incident[1],
                "msg_id": incident[2]
            }

            modal = IncidentModal(
                incident_id=incident["id"],
                rows=[
                    discord.ui.InputText(
                        label="Addtitional Comment",
                        placeholder="> The issue has been resolved.",
                        custom_id="comment",
                        max_length=512,
                        # style=2
                    )
                ]
            )
            await ctx.send_modal(modal)

        return


class IncidentModal(discord.ui.Modal):
    def __init__(self, incident_id: str, rows: list[discord.ui.InputText]):
        super().__init__(
            *rows,
            title="Resolve Incident",
            custom_id=f"resolve_incident-{incident_id}",
        )

    async def callback(self, ctx: Interaction):
        if not ctx.custom_id.startswith("resolve_incident-"):
            return

        incident_id = ctx.custom_id.split("-")[1]
        data = self.to_dict()
        nowTs = utcnow()

        async with aiosqlite.connect("./databases/statusUpdates.db") as db:
            await db.execute(
                "UPDATE incidents SET resolved_at = ? WHERE id = ?",
                (nowTs.isoformat(), incident_id)
            )
            await db.commit()

            incidentRow = await db.execute(
                "SELECT (id, title, msg_id) FROM incidents WHERE id = ?", (incident_id,)
            )
            incident = await incidentRow.fetchone()


def setup(bot):
    bot.add_cog(StatusUpdates(bot))
