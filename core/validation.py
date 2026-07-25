from models.workbook import FoamingWorkbook


def validate_start_number(foaming_path: str | None, start_number: int) -> None:
    """
    Raise ValueError if start_number would collide with an order already
    present in foaming_path's workbook. No-op if foaming_path is None —
    a blank workbook has nothing to collide with.

    Shared by GenerateWorker (checked once up front, for the primary
    uploaded workbook) and NewMonthDialog (checked interactively, for
    whichever workbook the user optionally uploads for a later month).
    """
    if foaming_path is None:
        return

    last_order_no = FoamingWorkbook.last_order_number(foaming_path)
    if last_order_no is not None and start_number <= last_order_no:
        raise ValueError(
            f"Starting order no. ({start_number}) must be greater "
            f"than the last order no. already in the foaming workbook "
            f"({last_order_no})."
        )