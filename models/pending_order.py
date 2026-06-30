from dataclasses import dataclass
from datetime import date


@dataclass
class PendingOrder:
    """
    A single row from the Pepperfry pending orders CSV.
    Field names map directly to CSV columns — no processing done here.
    """
    order_id:        str    # Order ID-SKU
    customer_name:   str    # Customer Name
    product_name:    str    # Product Name (full Pepperfry title)
    your_sku_id:     str    # Your SKU ID
    qty:             int    # QTY
    ship_before:     date   # To be shippped Before
    order_confirmed: date   # Order Confirmed Date