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
    "description": Optional[str],
    "updates": list[IncidentStatusUpdate],
    "created_at": datetime,
    "updated_at": Optional[datetime]
})

incidentColors = {
    "Down": 0xff3333,
    "Investigating": 0xfdff05,
    "Monitoring": 0x00ffa7,
    "Maintenance": 0x00a7ff,
    "Resolved": 0x44ff44
}

incidentEmojis = {
    "Down": "<:statusDown:1301964260221517994>",
    "Investigating": "<:statusInvestigating:1301964255238819930>",
    "Monitoring": "<:statusMonitor:1301964224502829067>",
    "Maintenance": "<:statusMaintenance:1301964247147741296>",
    "Resolved": "<:statusResolved:1301964214881095750>"
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
                return "We are currently performing maintenance. PLease be patient."
            case _:  # Resolved
                return "The issue has been resolved."


def format_incident(incident: Incident) -> Embed:
    """
    Format an incident to a Discord embed
    """
    return Embed(
        title=f'Incident {incident["id"]}',
        color=incidentColors[incident["updates"][-1]["status"].name],
        timestamp=incident["updated_at"],
        fields=[
            EmbedField(
                name=f'{incidentEmojis[update["status"].name]} [ <t:{int(update["updated_at"].timestamp())}:R> ] {update["status"].name}',
                value=format_update_content(update),
                inline=False
            ) for update in incident["updates"]
        ],
        footer=EmbedFooter(
            text="ID: " + incident["id"]
        )
    )
