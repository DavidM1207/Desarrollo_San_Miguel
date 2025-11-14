# -*- coding: utf-8 -*-
{
    'name': 'Employee Purchase Requisition - Fill Rate Report',
    'version': '17.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Reporte de Fill Rate para Requisiciones de Compra',
    'description': """
        Módulo de herencia que agrega:
        - Reporte de Fill Rate a nivel de líneas de requisición
        - Cálculo de cantidad recepcionada vs solicitada
        - Diferencia de días entre creación y recepción
        - Vista de solo lectura con menú separado
    """,
    'author': 'SAN MIGUEL MADERA, S.A.',
    'depends': [
        'employee_purchase_requisition',
        'stock',
        'purchase',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/requisition_order_fillrate_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
