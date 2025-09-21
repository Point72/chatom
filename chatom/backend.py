from typing import Literal, Union

DISCORD = "discord"
MATTERMOST = "mattermost"
MESSENGER = "messenger"
SLACK = "slack"
TEAMS = "teams"
TELEGRAM = "telegram"
WHATSAPP = "whatsapp"
ZULIP = "zulip"

Backend = Union[
    Literal[DISCORD],
    Literal[MATTERMOST],
    Literal[MESSENGER],
    Literal[SLACK],
    Literal[TEAMS],
    Literal[TELEGRAM],
    Literal[WHATSAPP],
    Literal[ZULIP],
    str,
]

__all__ = ("Backend", "DISCORD", "MATTERMOST", "MESSENGER", "SLACK", "TEAMS", "TELEGRAM", "WHATSAPP", "ZULIP")
