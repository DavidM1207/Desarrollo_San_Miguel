# -*- coding: utf-8 -*-
{
    'name': 'Employee Purchase Requisition',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Gestión de Requisiciones de Compra con Reportes',
    'description': """
        Módulo de Requisiciones de Compra de Empleados
        ================================================
        * Gestión de requisiciones de compra
        * Reporte de Fill Rate
        * Análisis de cumplimiento de entregas
    """,
    'depends': [
        'base',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/fill_rate_report_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}