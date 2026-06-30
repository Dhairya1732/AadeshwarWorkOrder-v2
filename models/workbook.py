import io
from datetime import date
from openpyxl import load_workbook
from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from core.order_parser import OrderParser
from core.template_loader import SHEET_FOAMING, SHEET_CARPENTER, SHEET_SALES


class WorkbookManager:
    """
    Base class for managing a monthly Excel workbook.
    Loads an existing workbook uploaded by the user and appends new sheets to it.
    A new workbook is created only when the month changes.

    template_bytes  — raw .xlsx bytes from TemplateLoader.raw_bytes
    template_sheet  — which sheet name inside the template to copy from
    existing_path   — path to the user-uploaded active workbook
    month_key       — e.g. "Jul/26", used for the output filename
    """

    def __init__(self, existing_path: str, template_bytes: bytes,
                 template_sheet: str, month_key: str):
        self._source_path     = existing_path
        self._template_bytes  = template_bytes
        self._template_sheet  = template_sheet
        self._month_key       = month_key
        self._wb              = load_workbook(existing_path)

    def _copy_template(self, sheet_name: str) -> Worksheet:
        """
        Load a fresh copy of the template workbook from bytes, copy the
        relevant sheet into self._wb, and return it.
        Uses a temporary workbook to avoid the cross-workbook copy restriction
        in openpyxl — copy_worksheet only works within the same workbook.
        """
        tmp_wb = load_workbook(io.BytesIO(self._template_bytes))
        tmp_ws = tmp_wb[self._template_sheet]
        ws     = self._wb.copy_worksheet(tmp_ws)
        ws.title = sheet_name
        return ws

    def has_sheet(self, sheet_name: str) -> bool:
        return sheet_name in self._wb.sheetnames

    def save(self) -> str:
        """
        Save the workbook to the same directory as the uploaded workbook.
        Returns the full path written.
        """
        directory = "/".join(self._source_path.replace("\\", "/").split("/")[:-1])
        path      = f"{directory}/{self._filename()}"
        self._wb.save(path)
        return path

    def _filename(self) -> str:
        raise NotImplementedError

    @staticmethod
    def date_to_sheet_name(d: date) -> str:
        """
        Format a date as dd.mm.yyyy for use as a carpenter/sales sheet name.
        e.g. date(2026, 6, 21) → "21.06.2026"
        """
        return f"{d.day:02d}.{d.month:02d}.{d.year}"


class FoamingWorkbook(WorkbookManager):
    """
    One sheet per work order, named by the order number suffix.
    e.g. G1/Jul/47 → sheet name "47"
    """

    def __init__(self, existing_path: str, template_bytes: bytes, month_key: str):
        super().__init__(existing_path, template_bytes, SHEET_FOAMING, month_key)

    def add_order(self, wo_number: str, order_date: date, modified_delivery: date,
                  customer_name: str, order_id: str, product_name: str, qty: int) -> None:
        sheet_name = wo_number.split("/")[-1]   # "G1/Jul/47" → "47"

        if self.has_sheet(sheet_name):
            return   # order already exists in this workbook — skip

        ws = self._copy_template(sheet_name)
        self._fill(ws, wo_number, order_date, modified_delivery,
                   customer_name, order_id, product_name, qty)

    def _fill(self, ws: Worksheet, wo_number: str, order_date: date,
              modified_delivery: date, customer_name: str,
              order_id: str, product_name: str, qty: int) -> None:
        fmt = OrderParser.format_date

        ws["B4"]  = wo_number
        ws["E4"]  = fmt(order_date)
        ws["E5"]  = fmt(modified_delivery)
        ws["B8"]  = customer_name
        ws["B10"] = order_id
        ws["B13"] = product_name
        ws["E15"] = qty

    def _filename(self) -> str:
        month = self._month_key.replace("/", " ")
        return f"FO - {month}.xlsx"


class CarpenterWorkbook(WorkbookManager):
    """
    One sheet per order date, named dd.mm.yyyy.
    Multiple orders on the same date are appended as rows on the same sheet.
    """

    _DATA_START_ROW = 4

    def __init__(self, existing_path: str, template_bytes: bytes, month_key: str):
        super().__init__(existing_path, template_bytes, SHEET_CARPENTER, month_key)

    def add_order(self, wo_number: str, ship_before: date, sku_id: str,
                  order_id: str, qty: int, order_date: date) -> None:
        sheet_name = self.date_to_sheet_name(order_date)

        if not self.has_sheet(sheet_name):
            self._copy_template(sheet_name)

        ws       = self._wb[sheet_name]
        next_row = self._next_empty_row(ws)

        ws.cell(row=next_row, column=1).value = qty
        ws.cell(row=next_row, column=2).value = wo_number
        ws.cell(row=next_row, column=3).value = ship_before.strftime("%d/%m/%Y")
        ws.cell(row=next_row, column=4).value = sku_id
        # columns 5 (Fabric), 6 (Remark), 7 (Inches), 8 (Total Inches) — manual
        ws.cell(row=next_row, column=9).value = order_id

    def _next_empty_row(self, ws: Worksheet) -> int:
        row = self._DATA_START_ROW
        while ws.cell(row=row, column=1).value is not None:
            row += 1
        return row

    def _filename(self) -> str:
        month = self._month_key.replace("/", " ")
        return f"CA - {month}.xlsx"


class SalesWorkbook(WorkbookManager):
    """
    One sheet per order date, named dd.mm.yyyy.
    Multiple orders on the same date are appended as rows on the same sheet.
    """

    _DATA_START_ROW = 4

    def __init__(self, existing_path: str, template_bytes: bytes, month_key: str):
        super().__init__(existing_path, template_bytes, SHEET_SALES, month_key)

    def add_order(self, sr_no: int, wo_number: str, modified_delivery: date,
                  customer_name: str, product_name: str, order_id: str,
                  qty: int, order_date: date) -> None:
        sheet_name = self.date_to_sheet_name(order_date)

        if not self.has_sheet(sheet_name):
            self._copy_template(sheet_name)

        ws       = self._wb[sheet_name]
        next_row = self._next_empty_row(ws)

        ws.cell(row=next_row, column=1).value = sr_no
        ws.cell(row=next_row, column=2).value = modified_delivery.strftime("%d/%m/%Y")
        ws.cell(row=next_row, column=3).value = wo_number
        ws.cell(row=next_row, column=4).value = qty
        ws.cell(row=next_row, column=5).value = customer_name
        ws.cell(row=next_row, column=6).value = product_name
        # columns 7 (Fabric), 8 (Remark) — manual
        ws.cell(row=next_row, column=9).value = order_id
        # columns 10 (Dispatch Date), 11 (Foaming Team), 12 (Carpenter Team) — manual

    def _next_empty_row(self, ws: Worksheet) -> int:
        row = self._DATA_START_ROW
        while ws.cell(row=row, column=1).value is not None:
            row += 1
        return row

    def _filename(self) -> str:
        month = self._month_key.replace("/", " ")
        return f"SO - {month}.xlsx"