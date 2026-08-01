import threading

from PyQt6.QtCore import QThread, pyqtSignal

from core.order_parser import OrderParser
from core.template_loader import TemplateLoader
from core.sku_database import SkuDatabase
from core.sheet_builder import SheetBuilder
from core.validation import validate_start_number
from models.month_plan import MonthPlan
from models.work_order import WorkOrder


class GenerateWorker(QThread):
    """
    Runs the full work order generation pipeline off the main UI thread.
    Emits progress signals per sheet type so MainWindow can update its
    three progress bars independently.

    Also emits new_month_needed whenever OrderParser (see _prompt_new_month)
    discovers orders for a month it hasn't planned for yet — MainWindow
    must respond by calling set_new_month_result before this thread can
    continue, since it blocks on that.
    """

    foaming_progress   = pyqtSignal(int, str)   # (percent, status message)
    carpenter_progress = pyqtSignal(int, str)
    sales_progress      = pyqtSignal(int, str)
    finished            = pyqtSignal(int)        # files_written
    error                = pyqtSignal(str)
    new_month_needed     = pyqtSignal(str, object)   # (month_key, threading.Event to set() once answered)

    _template_loader = TemplateLoader()
    _sku_database    = SkuDatabase()

    def __init__(self, csv_path: str, foaming_path: str,
                 carpenter_path: str, sales_path: str, start_number: int):
        super().__init__()
        self._csv_path       = csv_path
        self._foaming_path   = foaming_path
        self._carpenter_path = carpenter_path
        self._sales_path     = sales_path
        self._start_number   = start_number
        self._new_month_result: MonthPlan | None = None   # filled by set_new_month_result

    def set_new_month_result(self, plan: MonthPlan) -> None:
        """Called from the GUI thread with the user's answer to a new_month_needed prompt."""
        self._new_month_result = plan

    def _prompt_new_month(self, month_key: str) -> MonthPlan:
        """
        Passed to OrderParser as on_new_month. Emits new_month_needed and
        blocks this thread on the accompanying Event until MainWindow's
        connected slot has shown the modal prompt on the GUI thread and
        reported the result back via set_new_month_result.
        """
        answered = threading.Event()
        self.new_month_needed.emit(month_key, answered)
        answered.wait()
        return self._new_month_result

    def run(self) -> None:
        try:
            # ── Step 0: Starting order no. can't collide with orders already
            # in the uploaded foaming workbook ──
            validate_start_number(self._foaming_path, self._start_number)
            
            # ── Step 1: Parse CSV and build WorkOrder list ──
            month1_plan = MonthPlan(
                start_number   = self._start_number,
                foaming_path   = self._foaming_path,
                carpenter_path = self._carpenter_path,
                sales_path     = self._sales_path,
            )
            parser = OrderParser()
            work_orders, month_plans = parser.parse(self._csv_path, month1_plan, self._prompt_new_month)

            # ── Step 2: Look up each order's custom SKU + fabric from the
            # database sheet, keyed by Pepperfry's "Your SKU ID". Falls back
            # to the old colour-stripped product name when a SKU has no
            # match in the sheet, or its Stripped Product Name cell is blank;
            # fabric simply stays blank in that case, for manual fill-in. ──
            self._sku_database.fetch()
            for wo in work_orders:
                custom_sku, fabric = self._sku_database.get(wo.source.pepperfry_sku_id)
                wo.custom_sku    = custom_sku or ""
                wo.stripped_name = custom_sku or WorkOrder.strip_colour(wo.source.product_name)
                wo.fabric        = fabric or ""

            # ── Step 3: Check for template changes ──
            self._template_loader.fetch()

            # ── Step 4: Build sheets ──
            builder = SheetBuilder(
                month_plans    = month_plans,
                template_bytes = self._template_loader.raw_bytes,
                csv_path       = self._csv_path,
            )

            total = len(work_orders)
            for i, wo in enumerate(work_orders, start=1):
                builder.add_to_foaming(wo)
                pct = int(i / total * 100)
                self.foaming_progress.emit(pct, f"{i} of {total} orders")

            for i, wo in enumerate(work_orders, start=1):
                builder.add_to_carpenter(wo)
                pct = int(i / total * 100)
                self.carpenter_progress.emit(pct, f"{i} of {total} orders")

            for i, wo in enumerate(work_orders, start=1):
                builder.add_to_sales(wo)
                pct = int(i / total * 100)
                self.sales_progress.emit(pct, f"{i} of {total} orders")

            # ── Step 5: Save all touched workbooks ──
            paths_written = builder.save_all()

            self.finished.emit(len(paths_written))

        except Exception as e:
            self.error.emit(str(e))