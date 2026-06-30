import re
from dataclasses import dataclass, field
from datetime import date

from models.pending_order import PendingOrder


# Matches colour description fragments like:
#   "in Grey & Beige Colour"
#   "In Mint Green Colour"
#   "in Steel Grey Color"
_COLOUR_RE = re.compile(
    r"\s+\bin\b\s+[\w\s&]+\bColou?r\b",
    re.IGNORECASE
)


@dataclass
class WorkOrder:
    """
    A processed order derived from a PendingOrder.
    Contains all derived fields needed to populate the three sheet types.
    fabric_code and customization start empty — filled manually by the user
    after sheets are generated.
    """
    # Generated
    work_order_no:     str

    # Derived from PendingOrder
    modified_delivery: date
    order_date:        date
    stripped_name:     str

    # Reference back to the raw order
    source:            PendingOrder = field(repr=False)

    # ── Convenience properties ──────────────────────────────────────────────────

    @property
    def order_id(self) -> str:
        return self.source.order_id

    @property
    def customer_name(self) -> str:
        return self.source.customer_name

    @property
    def product_name(self) -> str:
        """Full Pepperfry product name — used in foaming sheet."""
        return self.source.product_name

    @property
    def your_sku_id(self) -> str:
        return self.source.your_sku_id

    @property
    def qty(self) -> int:
        return self.source.qty

    @property
    def foaming_month(self) -> str:
        """Month key for foaming workbook — based on modified delivery date."""
        return self.modified_delivery.strftime("%b %y")   # e.g. "Jul 26"

    @property
    def sheet_month(self) -> str:
        """Month key for carpenter and sales workbooks — based on order date."""
        return self.order_date.strftime("%b %y")           # e.g. "Jul 26"

    # ── Static methods ──────────────────────────────────────────────────────────

    @staticmethod
    def strip_colour(name: str) -> str:
        """
        Remove the colour description fragment from a Pepperfry product name.
        If no colour fragment is found, returns the name unchanged.
        """
        return _COLOUR_RE.sub("", name).strip()