# -*- coding: utf-8 -*-
{
    'name': 'Fill Rate Report',
    'version': '17.0.1.0.0',
    'category': 'Purchase',
    'author': 'SAN MIGUEL, S.A.',
    'depends': ['employee_purchase_requisition', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/fill_rate_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}