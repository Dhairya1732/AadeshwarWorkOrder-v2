import pandas as pd
from datetime import date, timedelta
from typing import Callable

from models.month_plan import MonthPlan
from models.pending_order import PendingOrder
from models.work_order import WorkOrder


# Exact column names from the Pepperfry pending orders CSV export
_COL_ORDER_ID          = "Order ID-SKU"
_COL_QTY               = "QTY"
_COL_PRODUCT_NAME      = "Product Name"
_COL_PEPPERFRY_SKU_ID  = "SKU ID"
_COL_AADESHWAR_SKU_ID  = "Your SKU ID"
_COL_CUSTOMER_NAME     = "Customer Name"
_COL_SHIP_BEFORE       = "To be shippped Before"   # sic — Pepperfry typo
_COL_ORDER_DATE        = "Order Confirmed Date"
_COL_IMAGE_URL         = "Image url"

_DELIVERY_OFFSET       = timedelta(days=2)
_DATE_FORMAT           = "%d-%m-%y"
_DATETIME_FORMAT       = "%d-%m-%y %H:%M"


class OrderParser:
    """
    Reads a Pepperfry pending orders CSV and produces a list of WorkOrder
    objects, plus the MonthPlan used for each distinct workbook_month found.
    work_order_no and stripped_name are left blank — filled before SheetBuilder runs.

    The first workbook_month encountered uses month1_plan as-is — the
    primary Foaming/Carpenter/Sales files already selected in the main
    window. Every subsequent, previously-unseen workbook_month calls
    on_new_month(month_key) to get its own MonthPlan. This is the hook
    MainWindow uses to pause and prompt the user
    """

    def parse(self, csv_path: str, month1_plan: MonthPlan,
              on_new_month: Callable[[str], MonthPlan]) -> tuple[list[WorkOrder], dict[str, MonthPlan]]:
        """
        Read the CSV at csv_path and return (work_orders, month_plans).
        work_order_no is assigned sequentially per month, starting from
        that month's MonthPlan.start_number (see class docstring for how
        each month's plan is obtained).
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

        parsed_rows = [
            (
                row,
                self._parse_date(row[_COL_SHIP_BEFORE], _DATE_FORMAT),
                self._parse_date(row[_COL_ORDER_DATE], _DATETIME_FORMAT),
                self._parse_date(row[_COL_SHIP_BEFORE], _DATE_FORMAT) - _DELIVERY_OFFSET,
            )
            for _, row in df.iterrows()
        ]

        # Decide every distinct workbook_month's MonthPlan up front, in
        # chronological order of modified_delivery.
        earliest_delivery: dict[str, date] = {}
        for _, _, _, modified in parsed_rows:
            month_key = modified.strftime("%b %y")
            if month_key not in earliest_delivery or modified < earliest_delivery[month_key]:
                earliest_delivery[month_key] = modified

        month_plans: dict[str, MonthPlan] = {}
        for i, month_key in enumerate(sorted(earliest_delivery, key=earliest_delivery.get)):
            month_plans[month_key] = month1_plan if i == 0 else on_new_month(month_key)

        # Running order-number counter per month_key, seeded from each plan
        month_counters = {mk: plan.start_number for mk, plan in month_plans.items()}

        work_orders = []

        for row, ship_before, order_confirmed, modified in parsed_rows:
            # month_key matches WorkOrder.workbook_month exactly, so
            # SheetBuilder can look a plan up by the same key it already uses.
            month_key  = modified.strftime("%b %y")   # e.g. "Jul 26"
            month_abbr = modified.strftime("%b")        # e.g. "Jul" — used in wo_number

            wo_number = f"G1/{month_abbr}/{month_counters[month_key]}"
            month_counters[month_key] += 1

            source = PendingOrder(
                order_id          = str(row[_COL_ORDER_ID]).strip(),
                customer_name     = str(row[_COL_CUSTOMER_NAME]).strip(),
                product_name      = str(row[_COL_PRODUCT_NAME]).strip(),
                pepperfry_sku_id  = str(row[_COL_PEPPERFRY_SKU_ID]).strip(),
                aadeshwar_sku_id  = str(row[_COL_AADESHWAR_SKU_ID]).strip(),
                qty               = int(row[_COL_QTY]),
                ship_before       = ship_before,
                order_confirmed   = order_confirmed,
                image_url         = str(row[_COL_IMAGE_URL]).strip()
            )

            work_orders.append(WorkOrder(
                work_order_no     = wo_number,
                modified_delivery = modified,
                order_date        = order_confirmed,
                stripped_name     = "",     # filled by worker via WorkOrder.strip_colour()
                source            = source,
            ))

        return work_orders, month_plans

    # ── Helpers ─────────────────────────────────────────────────────────────────

    def _validate_columns(self, df: pd.DataFrame):
        required = {
            _COL_ORDER_ID, _COL_QTY, _COL_PRODUCT_NAME,
            _COL_AADESHWAR_SKU_ID, _COL_CUSTOMER_NAME,
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