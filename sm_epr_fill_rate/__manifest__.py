# -*- coding: utf-8 -*-
{
    'name': 'Employee Purchase Requisition - Fill Rate',
    'version': '17.0.1.0.0',
    'category': 'Purchase',
    'depends': ['employee_purchase_requisition', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_requisition_fill_rate_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}