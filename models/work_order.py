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
    def workbook_month(self) -> str:
        """
        Month key used for the Foaming, Carpenter, and Sales workbook
        FILENAMES — based on modified_delivery, the same date OrderParser
        uses to assign the month embedded in work_order_no (e.g.
        "G1/Jul/92" → modified_delivery falls in July, so this is "Jul 26").

        Deliberately NOT order_date: the 2-day ship-before offset can push
        modified_delivery into the next month from order_date (e.g. an
        order confirmed 27/06 with modified_delivery in July), and the
        workbook filename must match the WO number's month, not the literal
        order date, or G1/Jul/92 ends up filed under "CA - Jun 26" instead
        of "CA - Jul 26".

        Note: this is unrelated to the per-day SHEET name inside the
        carpenter/sales workbooks, which is based on order_date directly
        (see WorkbookManager.date_to_sheet_name) and is unaffected by this.
        """
        return self.modified_delivery.strftime("%b %y")   # e.g. "Jul 26"

    # ── Static methods ──────────────────────────────────────────────────────────

    @staticmethod
    def strip_colour(name: str) -> str:
        """
        Remove the colour description fragment from a Pepperfry product name.
        If no colour fragment is found, returns the name unchanged.
        """
        return _COLOUR_RE.sub("", name).strip()