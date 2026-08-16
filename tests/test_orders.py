"""Tests for paid report delivery. No network, no payment provider, no email."""

import datetime as dt
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.delivery import fulfil_order  # noqa: E402
from backend.mailer import ConsoleSender, build_message  # noqa: E402
from backend.orders import (  # noqa: E402
    DELIVERED,
    PAID,
    PENDING,
    OrderError,
    SQLiteOrderStore,
    create_order,
    mark_delivered,
    mark_paid,
    valid_email,
)
from backend.payments import PaymentError, get_provider  # noqa: E402


@pytest.fixture
def store(tmp_path: Path) -> SQLiteOrderStore:
    return SQLiteOrderStore(tmp_path / "orders.db")


@pytest.fixture
def order(store: SQLiteOrderStore):
    return create_order(store, "buyer@example.co.za", "# Review\nBody.",
                        ["lease.pdf"], 9900, risk_score=7, risk_band="High",
                        immediate_delivery_consent=True)


@pytest.mark.parametrize("address, ok", [
    ("a@b.co.za", True), ("first.last+tag@sub.example.com", True),
    ("nope", False), ("a@b", False), ("", False), ("a b@c.co.za", False),
])
def test_email_validation(address: str, ok: bool) -> None:
    assert valid_email(address) is ok


def test_new_order_is_pending_and_normalised(store: SQLiteOrderStore) -> None:
    created = create_order(store, "  MiXeD@Example.CO.ZA ", "R", ["a.pdf"], 9900)
    assert created.email == "mixed@example.co.za"
    assert created.status == PENDING
    assert created.amount_display == "R99.00"


def test_order_requires_a_report(store: SQLiteOrderStore) -> None:
    with pytest.raises(OrderError, match="no report"):
        create_order(store, "a@b.co.za", "   ", ["a.pdf"], 9900)


def test_order_requires_a_valid_address(store: SQLiteOrderStore) -> None:
    with pytest.raises(OrderError, match="email address"):
        create_order(store, "not-an-email", "R", ["a.pdf"], 9900)


# --- the rule that matters: pay first -------------------------------------

def test_unpaid_orders_are_never_delivered(store: SQLiteOrderStore, order) -> None:
    with pytest.raises(OrderError, match="only ever sent after payment"):
        mark_delivered(store, order.id)


def test_dev_provider_fails_closed(store: SQLiteOrderStore, order) -> None:
    """A deployment that forgot to configure a gateway must not give work away."""
    with pytest.raises(PaymentError, match="No payment provider is configured"):
        fulfil_order(store, order, get_provider("dev", allow_dev=False), ConsoleSender())
    assert store.get(order.id).status == "failed"


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(PaymentError, match="not implemented"):
        get_provider("payfast")


def test_happy_path_pays_sends_and_records(store: SQLiteOrderStore, order) -> None:
    sender = ConsoleSender()
    delivered = fulfil_order(store, order, get_provider("dev", allow_dev=True), sender)

    assert delivered.status == DELIVERED
    assert delivered.paid_at and delivered.delivered_at
    assert len(sender.sent) == 1
    assert sender.sent[0].to == "buyer@example.co.za"


def test_a_failed_send_leaves_the_order_recoverable(store: SQLiteOrderStore, order) -> None:
    """The reader has paid. Never record delivery that did not happen."""
    class Broken(ConsoleSender):
        def send(self, message):
            from backend.mailer import EmailError
            raise EmailError("mailbox unavailable")

    from backend.mailer import EmailError
    with pytest.raises(EmailError):
        fulfil_order(store, order, get_provider("dev", allow_dev=True), Broken())

    after = store.get(order.id)
    assert after.status != DELIVERED
    assert "delivery failed" in after.failure_reason
    assert after.report, "the report must survive so the send can be retried"


def test_repeated_callbacks_do_not_redeliver(store: SQLiteOrderStore, order) -> None:
    delivered = fulfil_order(store, order, get_provider("dev", allow_dev=True),
                             ConsoleSender())
    assert mark_paid(store, delivered.id, "dev", "ref-again").status == DELIVERED


# --- POPIA retention -------------------------------------------------------

def test_report_bodies_are_purged_but_the_order_survives(
    store: SQLiteOrderStore, order
) -> None:
    delivered = fulfil_order(store, order, get_provider("dev", allow_dev=True),
                             ConsoleSender())
    old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=60)).isoformat()
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE orders SET delivered_at = ? WHERE id = ?",
                           (old, delivered.id))

    assert store.purge_delivered_reports(older_than_days=30) == 1
    after = store.get(delivered.id)
    assert after.report is None
    assert after.status == DELIVERED and after.email and after.amount_cents == 9900


def test_recent_deliveries_are_not_purged(store: SQLiteOrderStore, order) -> None:
    fulfil_order(store, order, get_provider("dev", allow_dev=True), ConsoleSender())
    assert store.purge_delivered_reports(older_than_days=30) == 0


def test_purged_order_cannot_be_resent(store: SQLiteOrderStore, order) -> None:
    delivered = fulfil_order(store, order, get_provider("dev", allow_dev=True),
                             ConsoleSender())
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE orders SET report = NULL, status = ? WHERE id = ?",
                           (PAID, delivered.id))
    with pytest.raises(OrderError, match="nothing to send"):
        fulfil_order(store, store.get(delivered.id),
                     get_provider("dev", allow_dev=True), ConsoleSender())


# --- the delivery email ----------------------------------------------------

def test_delivery_email_carries_the_disclaimer_and_no_marketing() -> None:
    message = build_message("a@b.co.za", "# Review", ["Lease Agreement.pdf"],
                            9, "Critical", "abc123")
    assert "Critical risk" in message.subject
    assert message.attachment_name == "Lease_Agreement_review.pdf"
    assert "not legal advice" in message.body_text
    assert "primary South African source" in message.body_text
    assert "once-off delivery and not a subscription" in message.body_text


def test_the_attachment_is_a_real_pdf() -> None:
    message = build_message("a@b.co.za", "# Review\n\nBody.",
                            ["Lease Agreement.pdf"], 9, "Critical", "abc123")
    assert message.attachment_type == "application/pdf"
    assert message.attachment_bytes.startswith(b"%PDF")
    assert message.attachment_bytes.rstrip().endswith(b"%%EOF")


def test_the_html_body_is_branded_and_states_the_risk() -> None:
    """The covering email has to carry the verdict, not just an attachment."""
    message = build_message("a@b.co.za", "# Review", ["Lease.pdf"], 9,
                            "Critical", "abc123")
    assert "LEGAL-EYE" in message.body_html
    assert "Critical risk" in message.body_html
    assert "not legal advice" in message.body_html.lower()
    # Gmail strips <style> blocks, so every rule that matters must be inline.
    assert "<style" not in message.body_html.lower()
    # A remote or data: URI logo would be blocked before it ever rendered.
    assert "<img" not in message.body_html.lower()


def test_filenames_that_would_break_a_mail_header_are_cleaned() -> None:
    """Quotes and semicolons in a filename corrupt Content-Disposition."""
    message = build_message("a@b.co.za", "# Review",
                            ['My "Lease"; v2/final.pdf'], 3, "Moderate", "x1")
    assert message.attachment_name == "My_Lease_v2_final_review.pdf"


def test_an_unrenderable_review_still_reaches_the_reader(monkeypatch) -> None:
    """A typesetting failure must downgrade to Markdown, never lose the review."""
    import backend.report_pdf as report_pdf

    def explode(*args, **kwargs):
        raise RuntimeError("no font for that glyph")

    monkeypatch.setattr(report_pdf, "render_report_pdf", explode)
    message = build_message("a@b.co.za", "# Review\n\nThe body.",
                            ["Lease.pdf"], 5, "Elevated", "abc123")
    assert message.attachment_name.endswith(".md")
    assert message.attachment_type == "text/markdown"
    assert b"The body." in message.attachment_bytes


def test_marketing_consent_is_recorded_separately(store: SQLiteOrderStore) -> None:
    """Collecting an address to deliver is not consent to market to it (POPIA s 69)."""
    plain = create_order(store, "a@b.co.za", "R", ["a.pdf"], 9900)
    opted = create_order(store, "c@d.co.za", "R", ["a.pdf"], 9900,
                         marketing_opt_in=True)
    assert plain.marketing_opt_in is False
    assert store.get(opted.id).marketing_opt_in is True


# --- ECTA s 42(2)(d) consent ----------------------------------------------

def test_delivery_refused_without_consent_to_immediate_delivery(
    store: SQLiteOrderStore
) -> None:
    """The terms say consent is recorded before delivery. Enforce it in code.

    ECTA s 48 makes any clause excluding a Chapter VII right void, so the
    seven-day cooling-off right in s 44 falls away only where s 42(2)(d) is
    actually satisfied: the service began with the consumer's consent. No
    consent, no delivery.
    """
    order = create_order(store, "a@b.co.za", "R", ["x.pdf"], 9900)
    assert order.immediate_delivery_consent is False
    assert order.consent_at is None

    with pytest.raises(OrderError, match="consent to immediate delivery"):
        fulfil_order(store, order, get_provider("dev", allow_dev=True),
                     ConsoleSender())


def test_consent_is_timestamped_and_persisted(store: SQLiteOrderStore) -> None:
    order = create_order(store, "a@b.co.za", "R", ["x.pdf"], 9900,
                         immediate_delivery_consent=True)
    assert order.consent_at is not None
    reloaded = store.get(order.id)
    assert reloaded.immediate_delivery_consent is True
    assert reloaded.consent_at == order.consent_at


def test_consent_and_marketing_are_independent(store: SQLiteOrderStore) -> None:
    """Consenting to delivery is not consenting to marketing (POPIA s 69)."""
    order = create_order(store, "a@b.co.za", "R", ["x.pdf"], 9900,
                         immediate_delivery_consent=True)
    assert order.immediate_delivery_consent is True
    assert order.marketing_opt_in is False


# --- durable storage -------------------------------------------------------

def test_the_store_falls_back_to_sqlite_without_a_database_url(tmp_path) -> None:
    from backend.orders import SQLiteOrderStore, get_order_store

    store = get_order_store("", tmp_path / "orders.db")
    assert isinstance(store, SQLiteOrderStore)


def test_a_database_url_selects_postgres() -> None:
    """Selecting the store must not open a connection, so this needs no server."""
    from backend.orders import PostgresOrderStore, get_order_store

    store = get_order_store("postgresql://user:pw@example.invalid:6543/postgres")
    assert isinstance(store, PostgresOrderStore)
    assert store._table == "legal_eye.orders"


def test_an_unsafe_schema_name_is_refused() -> None:
    """The schema cannot be a bound parameter, so it must be validated instead."""
    from backend.orders import PostgresOrderStore

    with pytest.raises(OrderError, match="Unsafe schema"):
        PostgresOrderStore("postgresql://x@y/z", schema="public; drop table orders--")


def test_timestamps_survive_the_round_trip() -> None:
    """Order holds ISO strings; timestamptz hands back datetimes."""
    from datetime import datetime, timezone
    from backend.orders import _to_datetime, _to_iso

    original = "2026-08-16T14:30:00+00:00"
    assert _to_iso(_to_datetime(original)) == original
    assert _to_datetime(None) is None and _to_iso(None) is None
    assert _to_iso(datetime(2026, 1, 1, tzinfo=timezone.utc)) == "2026-01-01T00:00:00+00:00"
