# -*- coding: utf-8 -*-
{
    'name': 'Reporte Fill Rate Requisiciones',
    'version': '15.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Reporte de Fill Rate para Requisiciones de Compra',
    'description': """
        Reporte de Fill Rate para Requisiciones
        =========================================
        
        Este módulo agrega un reporte completo de Fill Rate (porcentaje de cumplimiento)
        para las requisiciones de compra.
        
        Características principales:
        ----------------------------
        * Cálculo automático de Fill Rate: (Cantidad Recibida / Cantidad Original) × 100
        * Wizard con múltiples filtros (fechas, requisiciones, productos, ubicaciones)
        * Categorización automática (Excelente, Bueno, Regular, Deficiente)
        * Múltiples vistas: Lista, Gráfica, Pivot
        * Análisis de variaciones y discrepancias
        * Navegación integrada a requisiciones y traslados
        * Filtros avanzados y agrupaciones
        
        Menú de acceso:
        ---------------
        Requisiciones > Reportes > Fill Rate
    """,
    'author': 'SAN MIGUEL',
    
    'license': 'LGPL-3',
    
    'depends': [
        'base',
        'stock',
        'employee_purchase_requisition',  # Módulo de requisiciones personalizadas
    ],
    
    'data': [
        # Seguridad
        'security/ir.model.access.csv',
        
        # Vistas
        'views/fill_rate_report_views.xml',
    ],
    
    'installable': True,
    'application': False,
    'auto_install': False,
}