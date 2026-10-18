import json
from typing import Any

from sqlalchemy.orm import Session

from .auth import CurrentUser
from .models import AuditEvent


def record_event(
    session: Session,
    user: CurrentUser,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    session.add(AuditEvent(
        organization_id=user.organization_id,
        actor_id=user.subject,
        actor_role=",".join(sorted(user.roles)),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload_json=json.dumps(payload or {}, sort_keys=True, default=str),
    ))
