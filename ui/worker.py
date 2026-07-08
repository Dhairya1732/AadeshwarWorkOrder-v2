from PyQt6.QtCore import QThread, pyqtSignal

from core.order_parser import OrderParser
from core.template_loader import TemplateLoader
from core.sheet_builder import SheetBuilder
from models.work_order import WorkOrder
from models.workbook import FoamingWorkbook


class GenerateWorker(QThread):
    """
    Runs the full work order generation pipeline off the main UI thread.
    Emits progress signals per sheet type so MainWindow can update its
    three progress bars independently.
    """

    foaming_progress   = pyqtSignal(int, str)   # (percent, status message)
    carpenter_progress = pyqtSignal(int, str)
    sales_progress      = pyqtSignal(int, str)
    finished            = pyqtSignal(int)        # files_written
    error                = pyqtSignal(str)

    _template_loader = TemplateLoader()

    def __init__(self, csv_path: str, foaming_path: str,
                 carpenter_path: str, sales_path: str, start_number: int):
        super().__init__()
        self._csv_path       = csv_path
        self._foaming_path   = foaming_path
        self._carpenter_path = carpenter_path
        self._sales_path     = sales_path
        self._start_number   = start_number

    def run(self) -> None:
        try:
            # ── Step 0: Starting order no. can't collide with orders already
            # in the uploaded foaming workbook ──
            last_order_no = FoamingWorkbook.last_order_number(self._foaming_path)
            if last_order_no is not None and self._start_number <= last_order_no:
                raise ValueError(
                    f"Starting order no. ({self._start_number}) must be greater "
                    f"than the last order no. already in the foaming workbook "
                    f"({last_order_no})."
                )
            
            # ── Step 1: Parse CSV and build WorkOrder list ──
            parser = OrderParser()
            work_orders = parser.parse(self._csv_path, self._start_number)

            # ── Step 2: Strip colour from product names ──
            for wo in work_orders:
                wo.stripped_name = WorkOrder.strip_colour(wo.source.product_name)

            # ── Step 3: Check for template changes ──
            self._template_loader.fetch()

            # ── Step 4: Build sheets ──
            builder = SheetBuilder(
                foaming_path   = self._foaming_path,
                carpenter_path = self._carpenter_path,
                sales_path     = self._sales_path,
                template_bytes = self._template_loader.raw_bytes,
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