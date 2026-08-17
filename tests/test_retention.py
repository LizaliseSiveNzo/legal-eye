"""The retention promise is kept, and a failure to keep it is survivable.

The privacy notice publishes a specific number of days. These tests cover the
two things that matter: reports past the window actually get dropped, and a
store that is unreachable degrades quietly instead of taking the app down with
it.
"""

from __future__ import annotations

import datetime as dt

import pytest

from backend.orders import SQLiteOrderStore, create_order, mark_delivered, mark_paid
from backend.retention import PurgeResult, purge_reports


class BrokenStore:
    """A store whose database has gone away mid-request."""

    def purge_delivered_reports(self, older_than_days: int) -> int:
        raise ConnectionError("could not connect to server")


class CountingStore:
    def __init__(self, purged: int = 0) -> None:
        self.purged = purged
        self.calls: list[int] = []

    def purge_delivered_reports(self, older_than_days: int) -> int:
        self.calls.append(older_than_days)
        return self.purged


# --- The promise is kept ---------------------------------------------------

def test_purge_is_actually_called_with_the_retention_period():
    store = CountingStore()
    purge_reports(store, 30)
    assert store.calls == [30]


def test_result_reports_how_many_were_dropped():
    result = purge_reports(CountingStore(purged=3), 30)
    assert result.ok
    assert result.purged == 3
    assert "3 report(s) dropped" in str(result)


def test_nothing_due_is_not_an_error():
    result = purge_reports(CountingStore(purged=0), 30)
    assert result.ok
    assert "nothing due" in str(result)


# --- A failure must not break the app --------------------------------------

def test_unreachable_store_does_not_raise():
    result = purge_reports(BrokenStore(), 30)
    assert not result.ok
    assert result.purged == 0
    assert "could not connect" in result.error
    assert "failed" in str(result)


def test_negative_retention_is_rejected_rather_than_deleting_everything():
    """A misconfigured period must not be read as 'purge all history'."""
    store = CountingStore()
    result = purge_reports(store, -1)
    assert not result.ok
    assert store.calls == [], "the store must not be touched on a bad period"


# --- End to end against a real store ---------------------------------------

@pytest.fixture
def store(tmp_path) -> SQLiteOrderStore:
    return SQLiteOrderStore(tmp_path / "orders.db")


def _delivered_order(store: SQLiteOrderStore, days_ago: int):
    order = create_order(
        store, email="reader@example.co.za", document_names=["lease.pdf"],
        amount_cents=0, currency="ZAR", report="the full review text",
        risk_score=6, risk_band="Medium", immediate_delivery_consent=True,
    )
    mark_paid(store, order.id, "free", "no-charge")
    delivered = mark_delivered(store, order.id)

    # Backdate the delivery so the purge has something genuinely expired.
    when = (dt.datetime.now(dt.timezone.utc)
            - dt.timedelta(days=days_ago)).isoformat()
    with store._connect() as connection:  # noqa: SLF001 — test reaches in deliberately
        connection.execute("UPDATE orders SET delivered_at = ? WHERE id = ?",
                           (when, delivered.id))
    return delivered


def test_expired_report_body_is_dropped_but_the_order_survives(store):
    order = _delivered_order(store, days_ago=45)

    result = purge_reports(store, 30)
    assert result.ok and result.purged == 1

    after = store.get(order.id)
    assert after is not None, "the order record is the financial record and stays"
    assert not after.report, "the report body should be gone"


def test_report_inside_the_window_is_left_alone(store):
    order = _delivered_order(store, days_ago=5)

    result = purge_reports(store, 30)
    assert result.ok and result.purged == 0
    assert store.get(order.id).report, "a recent review must not be purged"
