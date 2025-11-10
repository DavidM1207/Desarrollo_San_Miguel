# -*- coding: utf-8 -*-
{
    'name': 'Reporte Fill Rate Requisiciones',
    'version': '15.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Reporte de Fill Rate para Requisiciones de Compra',
    'author': 'SAN MIGUEL',
 
    'license': 'LGPL-3',
    'depends': [
        'base',
        'stock',
        'employee_purchase_requisition',
    ],
    'data': [
        'views/fill_rate_report_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}