from dataclasses import dataclass


@dataclass
class MonthPlan:
    """
    Where one workbook_month's orders should go: which order number to
    start numbering from, and which existing Foaming/Carpenter/Sales
    workbooks (if any) to continue from.

    Pepperfry's three workbooks are always maintained together, so the
    three paths are all-or-nothing
    """
    start_number:   int
    foaming_path:   str | None
    carpenter_path: str | None
    sales_path:     str | None