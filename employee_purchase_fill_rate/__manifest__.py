# employee_purchase_fill_rate/__manifest__.py
{
    "name": "Employee Purchase Requisition - Fill Rate",
    "version": "17.0.1.0.0",
    "summary": "Reporte de Fill Rate para requisiciones internas (sin SQL, solo Python/ORM).",
    "author": "San Miguel / Custom",
    "depends": [
        "stock",
        "purchase",
        "employee_purchase_requisition",  # AJUSTA al nombre real de tu módulo base
    ],
    "data": [
        "views/fill_rate_views.xml",
    ],
    "installable": True,
    "application": False,
}
