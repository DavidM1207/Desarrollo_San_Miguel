# -*- coding: utf-8 -*-
{
    'name': 'Employee Purchase Requisition - Fill Rate',
    'version': '17.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Reporte de Fill Rate para Employee Purchase Requisition',
    'description': """
        Módulo que agrega un reporte de Fill Rate para el módulo employee.purchase.requisition.
        Muestra la relación entre unidades solicitadas y unidades entregadas.
    """,
    'author': 'SAN MIGUEL, S.A.',
    'depends': ['employee_purchase_requisition', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_requisition_fill_rate_views.xml',
        'data/fill_rate_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}