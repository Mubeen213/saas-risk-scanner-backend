from datetime import datetime
from typing import Any

from app.integrations.core.types import (
    UnifiedGroup,
    UnifiedGroupMembership,
    UnifiedTokenEvent,
    UnifiedUser,
)


def adapt_google_user(raw_user: dict[str, Any]) -> UnifiedUser:
    name = raw_user.get("name", {})
    return UnifiedUser(
        provider_id=raw_user.get("id", ""),
        email=raw_user.get("primaryEmail", ""),
        full_name=name.get("fullName"),
        given_name=name.get("givenName"),
        family_name=name.get("familyName"),
        is_admin=raw_user.get("isAdmin", False),
        is_delegated_admin=raw_user.get("isDelegatedAdmin", False),
        org_unit_path=raw_user.get("orgUnitPath"),
        avatar_url=raw_user.get("thumbnailPhotoUrl"),
        raw_data=raw_user,
    )


def adapt_google_group(raw_group: dict[str, Any]) -> UnifiedGroup:
    return UnifiedGroup(
        provider_id=raw_group.get("id", ""),
        email=raw_group.get("email", ""),
        name=raw_group.get("name", ""),
        description=raw_group.get("description"),
        direct_members_count=int(raw_group.get("directMembersCount", 0)),
        raw_data=raw_group,
    )


def adapt_google_member(
    raw_member: dict[str, Any], group_id: str
) -> UnifiedGroupMembership:
    return UnifiedGroupMembership(
        user_provider_id=raw_member.get("id", ""),
        group_provider_id=group_id,
        role=raw_member.get("role", "MEMBER"),
    )


def adapt_google_token_event(raw_event: dict[str, Any]) -> UnifiedTokenEvent | None:
    actor = raw_event.get("actor", {})
    user_email = actor.get("email")
    if not user_email:
        return None

    events = raw_event.get("events", [])
    if not events:
        return None

    event = events[0]
    event_name = event.get("name", "")
    parameters = event.get("parameters", [])

    params_dict: dict[str, Any] = {}
    for param in parameters:
        name = param.get("name", "")
        if "value" in param:
            params_dict[name] = param["value"]
        elif "multiValue" in param:
            params_dict[name] = param["multiValue"]

    client_id = params_dict.get("client_id", "")
    if not client_id:
        return None

    event_time_str = raw_event.get("id", {}).get("time")
    event_time = None
    if event_time_str:
        try:
            event_time = datetime.fromisoformat(event_time_str.replace("Z", "+00:00"))
        except ValueError:
            pass

    return UnifiedTokenEvent(
        client_id=client_id,
        app_name=params_dict.get("app_name"),
        user_email=user_email,
        scopes=params_dict.get("scope", []),
        client_type=params_dict.get("client_type"),
        event_type=event_name,
        event_time=event_time,
        raw_data=raw_event,
    )


def adapt_google_users(raw_users: list[dict[str, Any]]) -> list[UnifiedUser]:
    return [adapt_google_user(u) for u in raw_users]


def adapt_google_groups(raw_groups: list[dict[str, Any]]) -> list[UnifiedGroup]:
    return [adapt_google_group(g) for g in raw_groups]


def adapt_google_members(
    raw_members: list[dict[str, Any]], group_id: str
) -> list[UnifiedGroupMembership]:
    return [
        adapt_google_member(m, group_id) for m in raw_members if m.get("type") == "USER"
    ]


def adapt_google_token_events(
    raw_events: list[dict[str, Any]],
) -> list[UnifiedTokenEvent]:
    events = []
    for raw_event in raw_events:
        event = adapt_google_token_event(raw_event)
        if event:
            events.append(event)
    return events
