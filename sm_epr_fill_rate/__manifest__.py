# -*- coding: utf-8 -*-
{
    'name': 'Purchase Requisition Fill Rate',
    'version': '17.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Reporte de Fill Rate para Requisiciones de Compra',
    'description': """
        Módulo que agrega un reporte de Fill Rate para las requisiciones de compra.
        Muestra la relación entre unidades solicitadas y unidades entregadas.
    """,
    'author': 'SAN MIGUEL, S.A.',
    'depends': ['base','purchase_requisition', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_requisition_fill_rate_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}