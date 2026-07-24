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
_DATE_FORMAT       = "%d-%m-%y"
_DATETIME_FORMAT   = "%d-%m-%y %H:%M"


class OrderParser:
    """
    Reads a Pepperfry pending orders CSV and produces a list of WorkOrder objects.
    Handles parsing, type conversion, and modified delivery date computation.
    work_order_no and stripped_name are left blank — filled before SheetBuilder runs.

    start_number only applies to the month matching reference_date's calendar
    month
    """

    def parse(self, csv_path: str, start_number: int, reference_date: date | None = None) -> list[WorkOrder]:
        """
        Read the CSV at csv_path and return one WorkOrder per row.
        work_order_no is assigned sequentially from start_number within the
        active month (see class docstring); reference_date defaults to today
        and is settable for tests.
        Raises ValueError if required columns are missing.
        Raises FileNotFoundError if the path does not exist.
        """
        df = pd.read_csv(csv_path)
        self._validate_columns(df)
        df = df.sort_values(
            by=_COL_ORDER_DATE,
            key=lambda col: pd.to_datetime(col, format=_DATETIME_FORMAT),
            ignore_index=True,
        )

        active_month = (reference_date or date.today()).strftime("%b/%y")

        work_orders = []
        # Track per-month counters for work order numbering
        month_counters: dict[str, int] = {}

        for _, row in df.iterrows():
            ship_before     = self._parse_date(row[_COL_SHIP_BEFORE], _DATE_FORMAT)
            order_confirmed = self._parse_date(row[_COL_ORDER_DATE], _DATETIME_FORMAT)
            modified        = ship_before - _DELIVERY_OFFSET

            # Internal counter key — includes year so e.g. Jul/26 and Jul/27
            # don't share a counter. Not used for display.
            counter_key = modified.strftime("%b/%y")    # e.g. "Jul/26"
            month_abbr  = modified.strftime("%b")        # e.g. "Jul" — used in wo_number

            # Assign work order number — resets per month.
            if counter_key not in month_counters:
                month_counters[counter_key] = start_number if counter_key == active_month else 1
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

    def _parse_date(self, value: str, fmt: str) -> date:
        """
        Parse a date string into a Python date object, using the explicit
        fmt for the column being read (see _DATE_FORMAT / _DATETIME_FORMAT
        above). Passing fmt explicitly avoids pandas' format-guessing, which 
        is slower and would otherwise default to month-first parsing, silently 
        misparsing dates like "09-07-26" as 7 September instead of 9 July.
        """
        return pd.to_datetime(value, format=fmt).date()

    @staticmethod
    def format_date(d: date) -> str:
        """
        Format a date as dd/mm/yyyy with leading zeroes.
        Used by SheetBuilder when writing dates into cells.
        """
        return d.strftime("%d/%m/%Y")