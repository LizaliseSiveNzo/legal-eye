"""Who is selling this service, in one place.

Every legally-mandated disclosure on the About, Terms and Privacy pages is
rendered from the facts below. Before this module existed the same details were
written as `[[PLACEHOLDER]]` tokens across three static HTML files, which meant
38 separate edits before launch and no way to tell, from code, whether they had
been done.

Two rules govern everything here:

1. **A wrong value is worse than a blank one.** These are disclosures required by
   ECTA s 43(1) and POPIA s 18. Inventing a registration number or an address to
   make a page look finished would be a false statement to a consumer in a
   document the law requires to be accurate. So anything not known is set to
   NOT_SET, renders as a visible warning, and is reported by
   `missing_disclosures()`.

2. **The pages describe what the software actually does.** The price, whether
   payment is taken at all, and the retention period are read from `config`
   rather than restated by hand, so the terms cannot drift away from the code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date

from backend import config

# Rendered in place of a required disclosure that has not been supplied. It is
# deliberately conspicuous: a page that reaches a reader with this text on it is
# a bug, and it should look like one rather than reading as though it were fine.
NOT_SET = "— TO BE COMPLETED BEFORE LAUNCH —"


def _env(name: str, default: str = NOT_SET) -> str:
    """Read a business detail from the environment, falling back to NOT_SET."""
    return os.getenv(name, "").strip() or default


@dataclass(frozen=True)
class Business:
    """The supplier behind Legal-Eye, as the disclosure rules require it stated."""

    # --- Identity -------------------------------------------------------
    # A sole proprietorship has no separate legal personality: the human being
    # is the supplier. That is why there is no registration number, no
    # directors and no "incorporated in" language anywhere in this file. Those
    # rows of the ECTA table are answered by saying so plainly, not left blank.
    trading_name: str = "Legal-Eye"
    # Defaulted from the name on every commit in this repository. It must match
    # the proprietor's identity document exactly, so it is env-overridable and
    # should be confirmed before launch rather than assumed correct.
    proprietor_name: str = field(
        default_factory=lambda: _env("BUSINESS_PROPRIETOR", "Lizalise Sive Nzo"))
    legal_form: str = "sole proprietorship"

    # --- Contact, ECTA s 43(1)(b) and (c) -------------------------------
    # Address and telephone are mandatory and cannot be inferred from anything
    # the repository knows, so they stay NOT_SET until supplied.
    physical_address: str = field(default_factory=lambda: _env("BUSINESS_ADDRESS"))
    phone: str = field(default_factory=lambda: _env("BUSINESS_PHONE"))
    # Defaulted to the address on the repository's commits. Worth replacing with
    # a dedicated support mailbox before launch: this one appears on a public
    # page as the address for complaints, refunds and POPIA requests.
    support_email: str = field(
        default_factory=lambda: _env("BUSINESS_EMAIL", "lizalisenzo@revidarch.com"))

    # --- Tax ------------------------------------------------------------
    # Not a registered VAT vendor. This is load-bearing: VAT Act s 65 makes it
    # an offence to hold out that a price includes VAT when you are not
    # registered, so no page may say "including VAT" while this is False.
    vat_registered: bool = False
    vat_number: str = ""

    # --- POPIA ----------------------------------------------------------
    # For a sole trader the Information Officer is the sole trader (POPIA s 1),
    # so this is not a separate appointment. Registration with the Information
    # Regulator is still required.
    @property
    def information_officer(self) -> str:
        return self.proprietor_name

    @property
    def legal_name(self) -> str:
        """How the supplier is named in a contract: the human, then the brand."""
        if self.proprietor_name == NOT_SET:
            return NOT_SET
        return f"{self.proprietor_name} trading as {self.trading_name}"

    # --- Cross-border processing, POPIA s 72 ----------------------------
    # The provider is described by category rather than brand. POPIA s 18(1)(g)
    # asks for "the recipient or category of recipients", and the material fact
    # for a reader deciding whether to upload is the country, not the vendor's
    # name. This also keeps the product white-labelled, which is a deliberate
    # standing decision elsewhere in the codebase.
    ai_provider_description: str = "a third-party artificial intelligence provider"
    ai_provider_country: str = field(
        default_factory=lambda: _env("AI_PROVIDER_COUNTRY",
                                     "the People's Republic of China"))
    # s 72(1)(b): the data subject consents to the transfer. This is the honest
    # basis for a self-serve tool, because the alternative in s 72(1)(a) needs a
    # signed agreement with the provider binding it to onward-transfer limits,
    # and no such agreement exists.
    section_72_basis: str = (
        "section 72(1)(b) of POPIA, being your consent to the transfer, which "
        "you give by choosing to upload a document"
    )

    # --- Values that must match the running code ------------------------
    @property
    def retention_days(self) -> int:
        return config.REPORT_RETENTION_DAYS

    @property
    def charging(self) -> bool:
        return config.PAYMENTS_ENABLED

    @property
    def price_display(self) -> str:
        """The price as a reader sees it, with no VAT claim attached."""
        rand = config.REPORT_PRICE_CENTS / 100
        symbol = "R" if config.REPORT_CURRENCY.upper() == "ZAR" else ""
        return f"{symbol}{rand:,.2f}"

    @property
    def effective_date(self) -> str:
        return date.today().strftime("%d %B %Y")

    @property
    def year(self) -> int:
        return date.today().year

    def missing_disclosures(self) -> list[str]:
        """Required details still unsupplied, named as the statute names them.

        Used by the pages to warn, and by the test suite to fail loudly rather
        than let a half-finished disclosure reach a reader.
        """
        required = {
            "Full name of the proprietor (ECTA s 43(1)(a))": self.proprietor_name,
            "Physical address (ECTA s 43(1)(b))": self.physical_address,
            "Telephone number (ECTA s 43(1)(b))": self.phone,
            "Email address (ECTA s 43(1)(c))": self.support_email,
        }
        return [label for label, value in required.items() if value == NOT_SET]

    def is_publishable(self) -> bool:
        """True when every mandatory disclosure has a real value."""
        return not self.missing_disclosures()


BUSINESS = Business()
