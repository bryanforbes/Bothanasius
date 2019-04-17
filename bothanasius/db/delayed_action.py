from __future__ import annotations

from gino.json_support import ObjectProperty, ArrayProperty
from sqlalchemy.dialects.postgresql import JSONB
from typing import Any, Optional, Dict

from .base import db, Base, DateTime


class DelayedAction(Base):
    __tablename__ = 'delayed_actions'

    id = db.Column(db.Integer(), primary_key=True)
    created_at = db.Column(DateTime(), nullable=False)
    expires = db.Column(DateTime(), nullable=False, index=True)
    event = db.Column(db.String(), nullable=False)
    profile = db.Column(JSONB(), nullable=False, default={})

    args: 'ArrayProperty[Any]' = db.ArrayProperty(default=[])
    kwargs: 'ObjectProperty[Dict[str, Any]]' = db.ObjectProperty(default={})

    @staticmethod
    async def get_active() -> Optional[DelayedAction]:
        return (
            await DelayedAction.query.order_by(DelayedAction.expires.asc())
            .limit(1)
            .gino.first()
        )

    @staticmethod
    async def get_by_event(event: str, *args: Any) -> Optional[DelayedAction]:
        query = DelayedAction.query.where(DelayedAction.event == event)

        for index, arg in enumerate(args):
            query = query.where(
                db.text(
                    f"(delayed_actions.profile #> '{{args,{index}}}')::text "
                    f"= '{arg}'"
                )
            )

        return await query.gino.first()

    @staticmethod
    async def delete_by_id(id: int) -> Optional[DelayedAction]:
        return (
            await DelayedAction.delete.where(DelayedAction.id == id)
            .returning(*DelayedAction)
            .gino.first()
        )

    @staticmethod
    async def delete_by_event(event: str, *args: Any) -> Optional[DelayedAction]:
        query = DelayedAction.delete.where(DelayedAction.event == event)

        for index, arg in enumerate(args):
            query = query.where(
                db.text(
                    f"(delayed_actions.profile #> '{{args,{index}}}')::text "
                    f"= '{arg}'"
                )
            )

        return await query.returning(*DelayedAction).gino.first()
