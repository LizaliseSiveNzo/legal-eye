"""Payment providers, behind one interface.

No gateway is committed to yet. Everything the app needs is expressed as a
protocol, so adding PayFast, Yoco, Paystack or Stripe later means writing one
class and changing one config value, not touching the delivery flow.

Two rules are enforced here rather than left to the integration:

1. A report is delivered only after a provider CONFIRMS payment. The app never
   trusts a browser redirect, because a redirect URL can be typed by anyone. Real
   providers must verify server-side, either by a signed webhook or by calling
   the provider back to confirm the reference.
2. The development provider refuses to run unless it is explicitly switched on,
   so a misconfigured deployment fails closed and gives work away by accident.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.orders import Order


class PaymentError(RuntimeError):
    """Raised when a checkout cannot be started or a callback cannot be trusted."""


@dataclass(frozen=True)
class Checkout:
    """Where to send the reader, and how to recognise them coming back."""

    redirect_url: str
    reference: str
    instructions: str = ""


class PaymentProvider(Protocol):
    name: str

    def start_checkout(self, order: Order, return_url: str) -> Checkout:
        """Begin a payment and return where to send the reader."""

    def confirm(self, order: Order, payload: dict) -> str:
        """Verify a provider callback. Return the provider reference, or raise.

        Implementations MUST verify server-side: check the webhook signature, or
        call the provider to confirm the reference and the amount. Never accept
        the amount or the status from the browser.
        """


class DevPaymentProvider:
    """Marks orders paid without taking money. For local testing only.

    Fails closed: it raises unless PAYMENTS_ALLOW_DEV is explicitly true, so a
    production deployment that forgot to configure a real provider stops rather
    than emailing paid work away for nothing.
    """

    name = "dev"

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def _guard(self) -> None:
        if not self.enabled:
            raise PaymentError(
                "No payment provider is configured. Set PAYMENT_PROVIDER to a real "
                "gateway, or set PAYMENTS_ALLOW_DEV=true to test without charging."
            )

    def start_checkout(self, order: Order, return_url: str) -> Checkout:
        self._guard()
        return Checkout(
            redirect_url=return_url,
            reference=f"dev-{order.id[:12]}",
            instructions=("Development mode. No money has been taken and no card "
                          "was charged."),
        )

    def confirm(self, order: Order, payload: dict) -> str:
        self._guard()
        return f"dev-{order.id[:12]}"


def get_provider(name: str, allow_dev: bool = False) -> PaymentProvider:
    """Return the configured provider.

    When you add a gateway, implement the protocol above and register it here.
    A sketch of what each one needs:

      PayFast  - build a signed form post to the process URL, then verify the
                 ITN callback by posting it back to PayFast for validation and
                 checking the amount matches the order.
      Yoco     - create a checkout via the API, verify the webhook signature
                 against your webhook secret.
      Paystack - initialise a transaction, then verify by calling the verify
                 endpoint with the reference before trusting it.
      Stripe   - create a Checkout Session, verify the webhook signature with
                 the signing secret and confirm payment_status is 'paid'.

    In every case the amount must be re-checked against the order. A reader who
    edits a form should not be able to buy a report for one rand.
    """
    key = (name or "dev").strip().lower()
    if key in ("", "dev", "none"):
        return DevPaymentProvider(enabled=allow_dev)
    raise PaymentError(
        f"Payment provider '{name}' is not implemented yet. Implement the "
        "PaymentProvider protocol in backend/payments.py and register it in "
        "get_provider()."
    )
