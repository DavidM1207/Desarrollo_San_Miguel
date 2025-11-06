# -*- coding: utf-8 -*-
{
    'name': 'Fill Rate Report - Requisiciones',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Reporte de Fill Rate para Requisiciones de Compra de Empleados',
    'description': """
        Módulo de Reporte Fill Rate
        ============================
        
        Este módulo agrega un reporte de Fill Rate para el módulo de
        requisiciones de compra de empleados.
        
        Características principales:
        ----------------------------
        * Reporte dinámico de Fill Rate por producto y requisición
        * Análisis de cumplimiento de entregas vs solicitudes
        * Filtros avanzados por fechas y rangos de Fill Rate
        * Vistas de análisis: lista, pivot y gráficos
        * Solo considera transferencias internas completadas
        * Actualización automática basada en movimientos de inventario
        
        El Fill Rate se calcula como:
        (Cantidad Entregada / Cantidad Solicitada) × 100
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'stock',
        'employee_purchase_requisition',  # Módulo base de requisiciones
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/fill_rate_report_views.xml',
        'views/menu.xml',
        'wizard/fill_rate_diagnostic_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
