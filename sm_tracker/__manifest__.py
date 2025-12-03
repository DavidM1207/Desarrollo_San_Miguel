# -*- coding: utf-8 -*-
{
    'name': 'Tracker - Gestión de Proyectos y Tareas de Servicio',
    'version': '17.0.1.0.0',
    'category': 'Services/Project',
    'summary': 'Módulo para rastrear tiempo de trabajo en tareas de servicio desde ventas',
    'description': """
        Tracker - Gestión de Proyectos y Tareas de Servicio
        =====================================================
        
        Características principales:
        * Generación automática de proyectos desde órdenes de venta
        * Extracción de servicios desde BoMs con cálculo de cantidades
        * Control automático de tiempo de trabajo
        * Estados con seguimiento completo
        * Asignación de operarios
        * Registros de tiempo no editables
    """,
    'author': 'SAN MIGUEL MADERA, S.A.',
 
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale_management',
        'mrp',
        'analytic',
        'point_of_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/tracker_sequence.xml',
        'views/tracker_project_views.xml',
        'views/tracker_task_views.xml',
        'views/tracker_timesheet_views.xml',
        'views/tracker_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}