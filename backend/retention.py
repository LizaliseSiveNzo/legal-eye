"""Enforcing the retention promise the privacy notice makes.

The privacy notice tells every reader that a delivered review is "deleted N days
after delivery". `OrderStore.purge_delivered_reports` has always been able to do
that, and has always been tested, but until now nothing called it at runtime —
so the promise was made and never kept. POPIA s 14 requires that records not be
retained longer than necessary, and a published retention period that the code
does not honour is worse than having no period at all, because it is a statement
to the data subject that happens to be false.

Two design points, both deliberate:

**A purge failure must never break the app.** If the database is briefly
unreachable, a reader uploading a contract should not see an error about
housekeeping they did not ask for. `purge_reports` therefore catches everything
and reports the outcome rather than raising.

**The order record survives; only the report body is dropped.** The order is the
financial record and is kept for tax purposes, which is what the privacy notice
says. That distinction lives in the store implementations, not here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


class SupportsPurge(Protocol):
    def purge_delivered_reports(self, older_than_days: int) -> int: ...


@dataclass(frozen=True)
class PurgeResult:
    """What the purge did, in a form the caller can log or display."""

    purged: int = 0
    ok: bool = True
    error: str = ""

    def __str__(self) -> str:
        if not self.ok:
            return f"retention purge failed: {self.error}"
        if not self.purged:
            return "retention purge: nothing due"
        return f"retention purge: {self.purged} report(s) dropped"


def purge_reports(store: SupportsPurge, older_than_days: int) -> PurgeResult:
    """Drop report bodies past the retention window.

    Never raises. A failure here is an operational problem to be logged, not a
    reason to stop someone reviewing a contract.
    """
    if older_than_days < 0:
        return PurgeResult(ok=False, error=f"invalid retention period: {older_than_days}")

    try:
        purged = store.purge_delivered_reports(older_than_days)
    except Exception as exc:  # noqa: BLE001 — deliberately broad, see docstring
        logger.warning("Retention purge failed: %s", exc, exc_info=True)
        return PurgeResult(ok=False, error=str(exc))

    result = PurgeResult(purged=int(purged or 0))
    if result.purged:
        logger.info("Retention purge dropped %d report(s) older than %d days",
                    result.purged, older_than_days)
    return result
