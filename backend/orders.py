"""Order lifecycle for paid report delivery.

The flow is deliberately pay-first: an order is created when the reader asks for
their report by email, it is marked paid only when the payment provider confirms,
and the report is emailed only after that. Unpaid work is never delivered.

Storage sits behind a small interface. SQLite is the default so the app runs
with no external service, and a Supabase-backed store can be dropped in without
touching the callers. The SQL migration in sql/001_orders.sql creates the same
shape in Postgres.

POPIA note: an order row holds an email address and the full report, which
together are personal information. Two controls are built in rather than left to
policy. Marketing consent is stored separately from the delivery record, because
collecting an address to deliver a report is not a basis to market to it later
(s 69). And purge_delivered_reports() drops report bodies once they are no longer
needed, so the retention limit in s 14 is enforced by code on a schedule rather
than by good intentions.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

# Deliberately permissive. The address is verified by whether the report
# arrives, not by a regex trying to encode RFC 5322.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")

PENDING, PAID, DELIVERED, FAILED, REFUNDED = (
    "pending", "paid", "delivered", "failed", "refunded",
)


class OrderError(RuntimeError):
    """Raised when an order is asked to do something its state does not allow."""


def valid_email(address: str) -> bool:
    return bool(_EMAIL_RE.match((address or "").strip()))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Order:
    """One request to have a report delivered by email."""

    id: str
    email: str
    document_names: list[str]
    amount_cents: int
    currency: str = "ZAR"
    status: str = PENDING
    risk_score: int | None = None
    risk_band: str | None = None
    report: str | None = None
    provider: str | None = None
    provider_reference: str | None = None
    marketing_opt_in: bool = False
    # ECTA s 42(2)(d): the seven-day cooling-off right in s 44 does not apply to
    # a service that began with the consumer's consent before the seven days had
    # passed. That consent has to be real, separate and recorded, otherwise it
    # reads as an attempt to exclude a Chapter VII right, which s 48 makes void.
    immediate_delivery_consent: bool = False
    consent_at: str | None = None
    created_at: str = field(default_factory=_now)
    paid_at: str | None = None
    delivered_at: str | None = None
    failure_reason: str | None = None

    @property
    def amount_display(self) -> str:
        symbol = "R" if self.currency == "ZAR" else f"{self.currency} "
        return f"{symbol}{self.amount_cents / 100:,.2f}"

    def is_deliverable(self) -> bool:
        return self.status == PAID and bool(self.report)


class OrderStore(Protocol):
    """Anything that can persist orders. Implement this to swap in Supabase."""

    def save(self, order: Order) -> None: ...
    def get(self, order_id: str) -> Order | None: ...
    def purge_delivered_reports(self, older_than_days: int) -> int: ...


class SQLiteOrderStore:
    """Default store. One file, no service to run, fine to several thousand orders."""

    def __init__(self, path: str | Path = "orders.db") -> None:
        self.path = str(path)
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _migrate(self) -> None:
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    document_names TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    status TEXT NOT NULL,
                    risk_score INTEGER,
                    risk_band TEXT,
                    report TEXT,
                    provider TEXT,
                    provider_reference TEXT,
                    marketing_opt_in INTEGER NOT NULL DEFAULT 0,
                    immediate_delivery_consent INTEGER NOT NULL DEFAULT 0,
                    consent_at TEXT,
                    created_at TEXT NOT NULL,
                    paid_at TEXT,
                    delivered_at TEXT,
                    failure_reason TEXT
                )
            """)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS orders_status ON orders(status)")
            # Databases created before consent was recorded need the columns added.
            existing = {row["name"] for row in
                        connection.execute("PRAGMA table_info(orders)")}
            for column, definition in (
                ("immediate_delivery_consent", "INTEGER NOT NULL DEFAULT 0"),
                ("consent_at", "TEXT"),
            ):
                if column not in existing:
                    connection.execute(
                        f"ALTER TABLE orders ADD COLUMN {column} {definition}")

    def save(self, order: Order) -> None:
        data = asdict(order)
        data["document_names"] = json.dumps(order.document_names)
        data["marketing_opt_in"] = int(order.marketing_opt_in)
        data["immediate_delivery_consent"] = int(order.immediate_delivery_consent)
        columns = ", ".join(data)
        placeholders = ", ".join(f":{k}" for k in data)
        with self._connect() as connection:
            connection.execute(
                f"INSERT OR REPLACE INTO orders ({columns}) VALUES ({placeholders})",
                data,
            )

    def get(self, order_id: str) -> Order | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["document_names"] = json.loads(data["document_names"])
        data["marketing_opt_in"] = bool(data["marketing_opt_in"])
        data["immediate_delivery_consent"] = bool(data["immediate_delivery_consent"])
        return Order(**data)

    def purge_delivered_reports(self, older_than_days: int = 30) -> int:
        """Drop report bodies from orders delivered more than N days ago.

        The order itself is kept, because it is the financial record. Only the
        document text goes, which is the part that is personal information the
        business no longer needs.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE orders SET report = NULL "
                "WHERE status = ? AND delivered_at IS NOT NULL "
                "AND delivered_at < ? AND report IS NOT NULL",
                (DELIVERED, cutoff),
            )
            return cursor.rowcount


_SCHEMA_RE = re.compile(r"^[a-z_][a-z0-9_]*$")

_COLUMNS = (
    "id", "email", "document_names", "amount_cents", "currency", "status",
    "risk_score", "risk_band", "report", "provider", "provider_reference",
    "marketing_opt_in", "immediate_delivery_consent", "consent_at",
    "created_at", "paid_at", "delivered_at", "failure_reason",
)
_TIMESTAMPS = ("consent_at", "created_at", "paid_at", "delivered_at")


def _to_datetime(value: str | None) -> datetime | None:
    """ISO string to datetime, for a timestamptz column."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _to_iso(value) -> str | None:
    """Whatever Postgres handed back, as the ISO string the Order expects."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


class PostgresOrderStore:
    """Orders in Postgres, for any deployment whose disk does not survive.

    This exists because SQLite on Streamlit Community Cloud is a trap. The
    container filesystem is rebuilt whenever the app restarts, so orders.db and
    every order in it disappear without an error anywhere: the retention purge
    has nothing to purge, a delivery cannot be retried, and the POPIA record of
    what was sent to whom is simply gone.

    A connection is opened per operation rather than held open. Streamlit reruns
    the script constantly and a cached connection goes stale across reruns, while
    the order volume here is a handful of statements per delivery, so the
    simplest correct thing is also fast enough.
    """

    def __init__(self, dsn: str, schema: str = "legal_eye") -> None:
        if not dsn:
            raise OrderError("No database URL was configured.")
        if not _SCHEMA_RE.match(schema):
            # A schema name cannot be a bound parameter, so it is interpolated.
            # Validating it is what stops that being an injection point.
            raise OrderError(f"Unsafe schema name: {schema!r}")
        self.dsn = dsn
        self.schema = schema
        self._table = f"{schema}.orders"

    def _connect(self):
        import psycopg

        # prepare_threshold=None disables prepared statements. Supabase's
        # transaction-mode pooler hands a different backend connection to each
        # transaction, so a statement prepared on one is not there on the next.
        return psycopg.connect(self.dsn, prepare_threshold=None, connect_timeout=10)

    def save(self, order: Order) -> None:
        data = asdict(order)
        data["document_names"] = json.dumps(order.document_names)
        for key in _TIMESTAMPS:
            data[key] = _to_datetime(data[key])
        values = [data[column] for column in _COLUMNS]

        placeholders = ", ".join(
            "%s::jsonb" if column == "document_names" else "%s"
            for column in _COLUMNS
        )
        updates = ", ".join(
            f"{column} = excluded.{column}" for column in _COLUMNS if column != "id"
        )
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {self._table} ({', '.join(_COLUMNS)}) "
                f"VALUES ({placeholders}) "
                f"ON CONFLICT (id) DO UPDATE SET {updates}",
                values,
            )

    def get(self, order_id: str) -> Order | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {', '.join(_COLUMNS)} FROM {self._table} WHERE id = %s",
                (order_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        data = dict(zip(_COLUMNS, row))
        # jsonb comes back already decoded; a text column would not.
        if isinstance(data["document_names"], str):
            data["document_names"] = json.loads(data["document_names"])
        for key in _TIMESTAMPS:
            data[key] = _to_iso(data[key])
        data["marketing_opt_in"] = bool(data["marketing_opt_in"])
        data["immediate_delivery_consent"] = bool(data["immediate_delivery_consent"])
        return Order(**data)

    def purge_delivered_reports(self, older_than_days: int = 30) -> int:
        """Drop report bodies from orders delivered more than N days ago.

        Deliberately written in Python rather than calling the SQL function of
        the same name, so the behaviour is identical whichever store is in use.
        The order row stays, because it is the financial record; only the
        document text goes, which is the personal information no longer needed.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE {self._table} SET report = NULL "
                "WHERE status = %s AND delivered_at IS NOT NULL "
                "AND delivered_at < %s AND report IS NOT NULL",
                (DELIVERED, cutoff),
            )
            return cursor.rowcount


def get_order_store(database_url: str = "", sqlite_path: str | Path = "orders.db",
                    schema: str = "legal_eye") -> OrderStore:
    """Postgres when a database URL is configured, SQLite otherwise.

    Falling back to SQLite keeps local development working with no service to
    run. It is the wrong choice in a deployment with an ephemeral disk, so that
    case is logged loudly rather than passing silently.
    """
    if database_url:
        return PostgresOrderStore(database_url, schema=schema)
    logging.getLogger(__name__).warning(
        "No DATABASE_URL set, so orders are stored in the SQLite file %s. On a "
        "host with an ephemeral filesystem this loses every order on restart.",
        sqlite_path,
    )
    return SQLiteOrderStore(sqlite_path)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

def create_order(
    store: OrderStore,
    email: str,
    report: str,
    document_names: list[str],
    amount_cents: int,
    risk_score: int | None = None,
    risk_band: str | None = None,
    marketing_opt_in: bool = False,
    currency: str = "ZAR",
    immediate_delivery_consent: bool = False,
) -> Order:
    """Record a pending order. Nothing is charged and nothing is sent yet."""
    address = (email or "").strip().lower()
    if not valid_email(address):
        raise OrderError("That does not look like an email address.")
    if not report or not report.strip():
        raise OrderError("There is no report to deliver.")
    if amount_cents < 0:
        raise OrderError("An order cannot have a negative amount.")

    order = Order(
        id=uuid.uuid4().hex,
        email=address,
        document_names=list(document_names or []),
        amount_cents=amount_cents,
        currency=currency,
        risk_score=risk_score,
        risk_band=risk_band,
        report=report,
        marketing_opt_in=bool(marketing_opt_in),
        immediate_delivery_consent=bool(immediate_delivery_consent),
        consent_at=_now() if immediate_delivery_consent else None,
    )
    store.save(order)
    return order


def mark_paid(store: OrderStore, order_id: str, provider: str,
              provider_reference: str) -> Order:
    """Confirm payment. Only ever called from a verified provider callback."""
    order = store.get(order_id)
    if order is None:
        raise OrderError("Unknown order.")
    if order.status == DELIVERED:
        return order  # Already done; a repeated callback must not re-charge.
    if order.status not in (PENDING, FAILED):
        raise OrderError(f"An order in state '{order.status}' cannot be marked paid.")

    order.status = PAID
    order.provider = provider
    order.provider_reference = provider_reference
    order.paid_at = _now()
    order.failure_reason = None
    store.save(order)
    return order


def mark_delivered(store: OrderStore, order_id: str) -> Order:
    """Record that the report actually reached the reader."""
    order = store.get(order_id)
    if order is None:
        raise OrderError("Unknown order.")
    if order.status != PAID:
        raise OrderError(
            f"Refusing to mark an order delivered from state '{order.status}'. "
            "A report is only ever sent after payment is confirmed."
        )
    order.status = DELIVERED
    order.delivered_at = _now()
    store.save(order)
    return order


def mark_failed(store: OrderStore, order_id: str, reason: str) -> Order:
    order = store.get(order_id)
    if order is None:
        raise OrderError("Unknown order.")
    order.status = FAILED
    order.failure_reason = reason
    store.save(order)
    return order
