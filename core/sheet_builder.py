from models.work_order import WorkOrder
from models.workbook import FoamingWorkbook, CarpenterWorkbook, SalesWorkbook


class SheetBuilder:
    """
    Routes a list of WorkOrder objects into the correct monthly workbooks.
    Maintains one WorkbookManager per unique month encountered, keyed by
    month_key (e.g. "Jul/26"). New months get a fresh workbook starting
    from the user's uploaded active sheet.

    Usage:
        builder = SheetBuilder(foaming_path, carpenter_path, sales_path, template_bytes)
        builder.build(work_orders, progress_callback=...)
        paths = builder.save_all()
    """

    def __init__(self, foaming_path: str, carpenter_path: str,
                 sales_path: str, template_bytes: bytes):
        self._foaming_path   = foaming_path
        self._carpenter_path = carpenter_path
        self._sales_path     = sales_path
        self._template_bytes = template_bytes

        # One WorkbookManager per unique month encountered
        self._foaming_books:   dict[str, FoamingWorkbook]   = {}
        self._carpenter_books: dict[str, CarpenterWorkbook] = {}
        self._sales_books:     dict[str, SalesWorkbook]     = {}

    def build(self, work_orders: list[WorkOrder]) -> None:
        """
        Process every WorkOrder, writing it into the appropriate
        foaming, carpenter, and sales workbook.
        Convenience method for callers that don't need per-sheet-type
        progress tracking — for that, call add_to_foaming/carpenter/sales
        directly in separate loops instead (see GenerateWorker).
        """
        for wo in work_orders:
            self.add_to_foaming(wo)
            self.add_to_carpenter(wo)
            self.add_to_sales(wo)

    def save_all(self) -> list[str]:
        """
        Save every workbook touched during build() to disk.
        Returns a list of all file paths written.
        """
        paths = []
        for book in (
            *self._foaming_books.values(),
            *self._carpenter_books.values(),
            *self._sales_books.values(),
        ):
            paths.append(book.save())
        return paths

    # ── Foaming ─────────────────────────────────────────────────────────────────

    def add_to_foaming(self, wo: WorkOrder) -> None:
        month_key = wo.workbook_month   # e.g. "Jul 26" — based on modified_delivery, same as wo_number

        book = self._foaming_books.get(month_key)
        if book is None:
            book = FoamingWorkbook(self._foaming_path, self._template_bytes, month_key)
            self._foaming_books[month_key] = book

        book.add_order(
            wo_number          = wo.work_order_no,
            order_date          = wo.order_date,
            modified_delivery   = wo.modified_delivery,
            customer_name       = wo.customer_name,
            order_id            = wo.order_id,
            product_name        = wo.product_name,    # full name, not stripped
            qty                 = wo.qty,
        )

    # ── Carpenter ───────────────────────────────────────────────────────────────

    def add_to_carpenter(self, wo: WorkOrder) -> None:
        month_key = wo.workbook_month   # e.g. "Jul 26" — based on modified_delivery, same as wo_number

        book = self._carpenter_books.get(month_key)
        if book is None:
            book = CarpenterWorkbook(self._carpenter_path, self._template_bytes, month_key)
            self._carpenter_books[month_key] = book

        book.add_order(
            wo_number    = wo.work_order_no,
            ship_before  = wo.source.ship_before,
            sku_id       = wo.stripped_name,   # carpenter uses stripped name, not SKU
            order_id     = wo.order_id,
            qty          = wo.qty,
            order_date   = wo.order_date,   # per-day SHEET name within the workbook — unaffected by month_key above
        )

    # ── Sales ───────────────────────────────────────────────────────────────────

    def add_to_sales(self, wo: WorkOrder) -> None:
        month_key = wo.workbook_month   # e.g. "Jul 26" — based on modified_delivery, same as wo_number

        book = self._sales_books.get(month_key)
        if book is None:
            book = SalesWorkbook(self._sales_path, self._template_bytes, month_key)
            self._sales_books[month_key] = book

        book.add_order(
            wo_number           = wo.work_order_no,
            modified_delivery   = wo.modified_delivery,
            customer_name       = wo.customer_name,
            product_name        = wo.stripped_name,   # sales uses stripped name too
            order_id            = wo.order_id,
            qty                 = wo.qty,
            order_date          = wo.order_date,   # per-day SHEET name within the workbook — unaffected by month_key above
        )