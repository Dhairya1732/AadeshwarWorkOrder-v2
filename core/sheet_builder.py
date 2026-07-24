from datetime import date

from models.work_order import WorkOrder
from models.workbook import FoamingWorkbook, CarpenterWorkbook, SalesWorkbook


class SheetBuilder:
    """
    Routes a list of WorkOrder objects into the correct monthly workbooks.
    Maintains one WorkbookManager per unique month encountered, keyed by
    month_key (e.g. "Jul/26"). Only the month_key matching reference_date's
    calendar month continues from the user's uploaded active file — every
    other month_key gets a blank workbook.

    Usage:
        builder = SheetBuilder(foaming_path, carpenter_path, sales_path, template_bytes)
        builder.build(work_orders, progress_callback=...)
        paths = builder.save_all()
    """

    def __init__(self, foaming_path: str, carpenter_path: str,
                 sales_path: str, template_bytes: bytes, reference_date: date | None = None):
        self._foaming_path   = foaming_path
        self._carpenter_path = carpenter_path
        self._sales_path     = sales_path
        self._template_bytes = template_bytes

        # The one month_key allowed to continue from the uploaded active
        # file — everything else starts blank. reference_date is settable
        # for tests; real runs use today's calendar month.
        self._active_month = (reference_date or date.today()).strftime("%b %y")

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
    
    def _book_for(self, books: dict, month_key: str, path: str, cls):
        """
        Return the WorkbookManager for month_key in books, creating one if
        needed. Only month_key == self._active_month continues from the
        uploaded active file; every other month_key starts blank — this
        holds regardless of the order add_to_* is called in.
        """
        book = books.get(month_key)
        if book is None:
            book = cls(path, self._template_bytes, month_key, start_blank=month_key != self._active_month)
            books[month_key] = book
        return book

    # ── Foaming ─────────────────────────────────────────────────────────────────

    def add_to_foaming(self, wo: WorkOrder) -> None:
        month_key = wo.workbook_month   # e.g. "Jul 26" — based on modified_delivery, same as wo_number

        book = self._book_for(self._foaming_books, month_key, self._foaming_path, FoamingWorkbook)

        book.add_order(
            wo_number          = wo.work_order_no,
            order_date          = wo.order_date,
            modified_delivery   = wo.modified_delivery,
            customer_name       = wo.customer_name,
            order_id            = wo.order_id,
            product_name        = wo.product_name,    # full name, not stripped
            qty                 = wo.qty,
            image_url           = wo.source.image_url,
        )

    # ── Carpenter ───────────────────────────────────────────────────────────────

    def add_to_carpenter(self, wo: WorkOrder) -> None:
        month_key = wo.workbook_month   # e.g. "Jul 26" — based on modified_delivery, same as wo_number

        book = self._book_for(self._carpenter_books, month_key, self._carpenter_path, CarpenterWorkbook)

        book.add_order(
            wo_number          = wo.work_order_no,
            modified_delivery  = wo.modified_delivery,
            sku_id             = wo.stripped_name,   # carpenter uses stripped name, not SKU
            order_id           = wo.order_id,
            qty                = wo.qty,
            order_date         = wo.order_date,   # per-day SHEET name within the workbook — unaffected by month_key above
        )

    # ── Sales ───────────────────────────────────────────────────────────────────

    def add_to_sales(self, wo: WorkOrder) -> None:
        month_key = wo.workbook_month   # e.g. "Jul 26" — based on modified_delivery, same as wo_number

        book = self._book_for(self._sales_books, month_key, self._sales_path, SalesWorkbook)

        book.add_order(
            wo_number           = wo.work_order_no,
            modified_delivery   = wo.modified_delivery,
            customer_name       = wo.customer_name,
            product_name        = wo.stripped_name,   # sales uses stripped name too
            order_id            = wo.order_id,
            qty                 = wo.qty,
            order_date          = wo.order_date,   # per-day SHEET name within the workbook — unaffected by month_key above
        )