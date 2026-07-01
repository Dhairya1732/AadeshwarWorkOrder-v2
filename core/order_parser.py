import pandas as pd
from datetime import date, timedelta

from models.pending_order import PendingOrder
from models.work_order import WorkOrder


# Exact column names from the Pepperfry pending orders CSV export
_COL_ORDER_ID      = "Order ID-SKU"
_COL_QTY           = "QTY"
_COL_PRODUCT_NAME  = "Product Name"
_COL_YOUR_SKU_ID   = "Your SKU ID"
_COL_CUSTOMER_NAME = "Customer Name"
_COL_SHIP_BEFORE   = "To be shippped Before"   # sic — Pepperfry typo
_COL_ORDER_DATE    = "Order Confirmed Date"
_COL_IMAGE_URL     = "Image url"

_DELIVERY_OFFSET   = timedelta(days=2)


class OrderParser:
    """
    Reads a Pepperfry pending orders CSV and produces a list of WorkOrder objects.
    Handles parsing, type conversion, and modified delivery date computation.
    work_order_no and stripped_name are left blank — filled before SheetBuilder runs.
    """

    def parse(self, csv_path: str, start_number: int) -> list[WorkOrder]:
        """
        Read the CSV at csv_path and return one WorkOrder per row.
        work_order_no is assigned sequentially from start_number.
        Raises ValueError if required columns are missing.
        Raises FileNotFoundError if the path does not exist.
        """
        df = pd.read_csv(csv_path)
        self._validate_columns(df)

        work_orders = []
        # Track per-month counters for work order numbering
        month_counters: dict[str, int] = {}

        for _, row in df.iterrows():
            ship_before     = self._parse_date(row[_COL_SHIP_BEFORE])
            order_confirmed = self._parse_date(row[_COL_ORDER_DATE])
            modified        = ship_before - _DELIVERY_OFFSET

            # Internal counter key — includes year so e.g. Jul/26 and Jul/27
            # don't share a counter. Not used for display.
            counter_key = modified.strftime("%b/%y")    # e.g. "Jul/26"
            month_abbr  = modified.strftime("%b")        # e.g. "Jul" — used in wo_number

            # Assign work order number — resets per month, starts at start_number
            if counter_key not in month_counters:
                month_counters[counter_key] = start_number
            else:
                month_counters[counter_key] += 1

            wo_number = f"G1/{month_abbr}/{month_counters[counter_key]}"

            source = PendingOrder(
                order_id        = str(row[_COL_ORDER_ID]).strip(),
                customer_name   = str(row[_COL_CUSTOMER_NAME]).strip(),
                product_name    = str(row[_COL_PRODUCT_NAME]).strip(),
                your_sku_id     = str(row[_COL_YOUR_SKU_ID]).strip(),
                qty             = int(row[_COL_QTY]),
                ship_before     = ship_before,
                order_confirmed = order_confirmed,
                image_url       = str(row[_COL_IMAGE_URL]).strip()
            )

            work_orders.append(WorkOrder(
                work_order_no     = wo_number,
                modified_delivery = modified,
                order_date        = order_confirmed,
                stripped_name     = "",     # filled by worker via WorkOrder.strip_colour()
                source            = source,
            ))

        return work_orders

    # ── Helpers ─────────────────────────────────────────────────────────────────

    def _validate_columns(self, df: pd.DataFrame):
        required = {
            _COL_ORDER_ID, _COL_QTY, _COL_PRODUCT_NAME,
            _COL_YOUR_SKU_ID, _COL_CUSTOMER_NAME,
            _COL_SHIP_BEFORE, _COL_ORDER_DATE, _COL_IMAGE_URL,
        }
        missing = required - set(df.columns)
        if missing:
            raise ValueError(
                f"CSV is missing required columns: {', '.join(sorted(missing))}\n"
                f"Make sure you are uploading a Pepperfry pending orders export."
            )

    def _parse_date(self, value: str) -> date:
        """
        Parse a date string into a Python date object.
        Pepperfry exports dates as dd-mm-yy (e.g. "09-07-26" = 9 July 2026),
        so dayfirst=True is required — without it, pandas defaults to
        month-first parsing and only falls back to day-first when the first
        number can't possibly be a month (e.g. "27-06-26"), silently
        misparsing the rest (e.g. "09-07-26" becomes 7 September instead of
        9 July).
        """
        return pd.to_datetime(value, dayfirst=True).date()

    @staticmethod
    def format_date(d: date) -> str:
        """
        Format a date as dd/mm/yyyy with leading zeroes.
        Used by SheetBuilder when writing dates into cells.
        """
        return d.strftime("%d/%m/%Y")