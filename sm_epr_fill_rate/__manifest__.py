# -*- coding: utf-8 -*-
{
    'name': 'Employee Purchase Requisition - Fill Rate Report',
    'version': '17.0.1.0.0',
    'category': 'Purchase',
    'depends': [
        'employee_purchase_requisition',  # Tu módulo existente (ajusta el nombre si es diferente)
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/fill_rate_report_views.xml',
    ],
    'installable': True,
    'application': False,
}