from datetime import datetime
from typing import Optional, TypedDict, Union
from discord import Embed, EmbedField, EmbedFooter

from utils.enums import IncidentStatus

IncidentStatusUpdate = TypedDict("IncidentStatusUpdate", {
    "status_id": int,
    "status": IncidentStatus,
    "content": Optional[str],
    "updated_at": datetime
})

Incident = TypedDict("Incident", {
    "id": str,
    "title": str,
    "updates": list[IncidentStatusUpdate],
    "created_at": datetime,
    "updated_at": Optional[datetime]
})

incidentColors = {
    IncidentStatus.Down: 0xff3333,
    IncidentStatus.Investigating: 0xfdff05,
    IncidentStatus.Monitoring: 0x00ffa7,
    IncidentStatus.Maintenance: 0x00a7ff,
    IncidentStatus.Resolved: 0x44ff44
}

incidentEmojis = {
    IncidentStatus.Down: "<:statusDown:1301964260221517994>",
    IncidentStatus.Investigating: "<:statusInvestigating:1301964255238819930>",
    IncidentStatus.Monitoring: "<:statusMonitor:1301964224502829067>",
    IncidentStatus.Maintenance: "<:statusMaintenance:1301964247147741296>",
    IncidentStatus.Resolved: "<:statusResolved:1301964214881095750>"
}


def format_update_content(update: IncidentStatusUpdate) -> str:
    if update["content"]:
        return update['content']
    if not update["content"]:
        match update["status"]:
            case IncidentStatus.Down:
                return "We are currently experiencing issues. We are investigating the cause."
            case IncidentStatus.Investigating:
                return "We are currently investigating the issue."
            case IncidentStatus.Monitoring:
                return "We have identified the issue and are monitoring the situation."
            case IncidentStatus.Maintenance:
                return "We are currently performing maintenance. Please be patient."
            case _:  # Resolved
                return "The issue has been resolved."


def format_incident(incident: Incident) -> Embed:
    """
    Format an incident to a Discord embed
    """
    startedAtTs = int(incident["created_at"].timestamp())

    return Embed(
        title=incident["title"],
        description=f'Started: <t:{startedAtTs}> (<t:{startedAtTs}:R>)' if len(incident["updates"]) > 1 else '',
        color=incidentColors[incident["updates"][-1]["status"]],
        timestamp=incident["updated_at"],
        fields=[
            EmbedField(
                name=f'{incidentEmojis[update["status"]]} [ <t:{int(update["updated_at"].timestamp())}:R> ] {update["status"].name}',
                value=format_update_content(update),
                inline=False
            ) for update in incident["updates"]
        ],
        footer=EmbedFooter(
            text=incident["id"]
        )
    )
