# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class FillRateDiagnosticWizard(models.TransientModel):
    _name = 'fill.rate.diagnostic.wizard'
    _description = 'Asistente de Diagnóstico Fill Rate'

    diagnostic_result = fields.Html(
        string='Resultado del Diagnóstico',
        readonly=True
    )
    action = fields.Selection([
        ('diagnose', 'Ejecutar Diagnóstico'),
        ('generate', 'Generar Datos del Reporte'),
        ('clear', 'Limpiar Datos del Reporte'),
    ], string='Acción', default='diagnose', required=True)

    def action_execute(self):
        """Ejecuta la acción seleccionada"""
        self.ensure_one()
        
        if self.action == 'diagnose':
            return self.action_run_diagnostic()
        elif self.action == 'generate':
            return self.action_generate_data()
        elif self.action == 'clear':
            return self.action_clear_data()

    def action_run_diagnostic(self):
        """Ejecuta el diagnóstico completo del sistema"""
        self.ensure_one()
        
        html_result = self._build_diagnostic_html()
        
        self.write({'diagnostic_result': html_result})
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Resultado del Diagnóstico'),
            'res_model': 'fill.rate.diagnostic.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _build_diagnostic_html(self):
        """Construye el HTML con los resultados del diagnóstico"""
        
        results = []
        
        # 1. Verificar módulo de requisiciones
        results.append(self._check_requisition_module())
        
        # 2. Verificar estructura de datos
        results.append(self._check_data_structure())
        
        # 3. Verificar relación con stock.move
        results.append(self._check_stock_move_relation())
        
        # 4. Verificar tipos de requisición
        results.append(self._check_requisition_types())
        
        # 5. Verificar movimientos completados
        results.append(self._check_completed_moves())
        
        # 6. Verificar datos actuales del reporte
        results.append(self._check_report_data())
        
        # Construir HTML
        html = """
        <div style="padding: 20px; font-family: Arial, sans-serif;">
            <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                🔍 Diagnóstico del Sistema Fill Rate
            </h2>
        """
        
        for result in results:
            html += result
        
        html += """
            <div style="margin-top: 30px; padding: 15px; background-color: #ecf0f1; border-radius: 5px;">
                <h3 style="color: #2c3e50; margin-top: 0;">Próximos Pasos</h3>
                <ol style="line-height: 1.8;">
                    <li>Revisa los puntos marcados en ⚠️ ADVERTENCIA o ❌ ERROR</li>
                    <li>Consulta el archivo INTEGRATION_GUIDE.md para ajustes específicos</li>
                    <li>Ejecuta "Generar Datos del Reporte" después de hacer ajustes</li>
                    <li>Si todo está correcto, configura actualización automática</li>
                </ol>
            </div>
        </div>
        """
        
        return html

    def _check_requisition_module(self):
        """Verifica la instalación del módulo de requisiciones"""
        html = '<div style="margin: 20px 0; padding: 15px; background-color: #fff; border-left: 4px solid #3498db;">'
        html += '<h3 style="margin-top: 0; color: #2c3e50;">1️⃣ Módulo de Requisiciones</h3>'
        
        try:
            requisition_model = self.env['employee.purchase.requisition']
            count = requisition_model.search_count([])
            
            html += f'<p>✅ <strong>Modelo encontrado:</strong> employee.purchase.requisition</p>'
            html += f'<p>✅ <strong>Requisiciones en sistema:</strong> {count}</p>'
            
            if count == 0:
                html += '<p style="color: #e67e22;">⚠️ <strong>ADVERTENCIA:</strong> No hay requisiciones en el sistema</p>'
        except Exception as e:
            html += f'<p style="color: #e74c3c;">❌ <strong>ERROR:</strong> No se pudo acceder al modelo: {str(e)}</p>'
        
        html += '</div>'
        return html

    def _check_data_structure(self):
        """Verifica la estructura de datos de las requisiciones"""
        html = '<div style="margin: 20px 0; padding: 15px; background-color: #fff; border-left: 4px solid #3498db;">'
        html += '<h3 style="margin-top: 0; color: #2c3e50;">2️⃣ Estructura de Datos</h3>'
        
        try:
            requisition = self.env['employee.purchase.requisition'].search([], limit=1)
            
            if not requisition:
                html += '<p style="color: #e67e22;">⚠️ No hay requisiciones para analizar</p>'
            else:
                html += f'<p>✅ <strong>Requisición de prueba:</strong> {requisition.name}</p>'
                
                # Verificar líneas
                if requisition.requisition_order_ids:
                    line = requisition.requisition_order_ids[0]
                    html += f'<p>✅ <strong>Líneas encontradas:</strong> {len(requisition.requisition_order_ids)}</p>'
                    
                    # Verificar campos
                    fields_to_check = ['product_id', 'qty', 'requisition_type']
                    for field_name in fields_to_check:
                        if hasattr(line, field_name):
                            value = getattr(line, field_name)
                            html += f'<p>✅ Campo <code>{field_name}</code>: {value}</p>'
                        else:
                            html += f'<p style="color: #e74c3c;">❌ Campo <code>{field_name}</code> NO encontrado</p>'
                else:
                    html += '<p style="color: #e67e22;">⚠️ La requisición no tiene líneas</p>'
                    
        except Exception as e:
            html += f'<p style="color: #e74c3c;">❌ <strong>ERROR:</strong> {str(e)}</p>'
        
        html += '</div>'
        return html

    def _check_stock_move_relation(self):
        """Verifica la relación entre requisiciones y movimientos de stock"""
        html = '<div style="margin: 20px 0; padding: 15px; background-color: #fff; border-left: 4px solid #3498db;">'
        html += '<h3 style="margin-top: 0; color: #2c3e50;">3️⃣ Relación con Stock Moves</h3>'
        
        try:
            # Verificar si stock.move tiene campo requisition_line_id
            stock_move = self.env['stock.move']
            
            if hasattr(stock_move, 'requisition_line_id'):
                html += '<p>✅ <strong>Campo directo encontrado:</strong> requisition_line_id en stock.move</p>'
                
                moves_count = stock_move.search_count([('requisition_line_id', '!=', False)])
                html += f'<p>✅ <strong>Movimientos con requisición:</strong> {moves_count}</p>'
                
                if moves_count == 0:
                    html += '<p style="color: #e67e22;">⚠️ No hay movimientos asociados a requisiciones</p>'
            else:
                html += '<p style="color: #e67e22;">⚠️ <strong>Campo directo NO encontrado</strong></p>'
                html += '<p>💡 Necesitas usar relación alternativa (picking_id o origin)</p>'
                html += '<p>📖 Consulta INTEGRATION_GUIDE.md para más detalles</p>'
            
        except Exception as e:
            html += f'<p style="color: #e74c3c;">❌ <strong>ERROR:</strong> {str(e)}</p>'
        
        html += '</div>'
        return html

    def _check_requisition_types(self):
        """Verifica los tipos de requisición disponibles"""
        html = '<div style="margin: 20px 0; padding: 15px; background-color: #fff; border-left: 4px solid #3498db;">'
        html += '<h3 style="margin-top: 0; color: #2c3e50;">4️⃣ Tipos de Requisición</h3>'
        
        try:
            requisitions = self.env['employee.purchase.requisition'].search([])
            
            if not requisitions:
                html += '<p style="color: #e67e22;">⚠️ No hay requisiciones para analizar</p>'
            else:
                types_found = set()
                type_counts = {}
                
                for req in requisitions:
                    for line in req.requisition_order_ids:
                        if hasattr(line, 'requisition_type'):
                            req_type = line.requisition_type
                            types_found.add(req_type)
                            type_counts[req_type] = type_counts.get(req_type, 0) + 1
                
                if types_found:
                    html += '<p><strong>Tipos encontrados:</strong></p><ul>'
                    for req_type, count in type_counts.items():
                        emoji = '✅' if req_type == 'internal_transfer' else '⚠️'
                        html += f'<li>{emoji} <code>{req_type}</code>: {count} líneas</li>'
                    html += '</ul>'
                    
                    if 'internal_transfer' not in types_found:
                        html += '<p style="color: #e67e22;">⚠️ <strong>ADVERTENCIA:</strong> No se encontró tipo "internal_transfer"</p>'
                        html += f'<p>💡 Actualiza el código para usar: <code>{list(types_found)[0]}</code></p>'
                else:
                    html += '<p style="color: #e67e22;">⚠️ No se encontró el campo requisition_type</p>'
                    
        except Exception as e:
            html += f'<p style="color: #e74c3c;">❌ <strong>ERROR:</strong> {str(e)}</p>'
        
        html += '</div>'
        return html

    def _check_completed_moves(self):
        """Verifica movimientos completados"""
        html = '<div style="margin: 20px 0; padding: 15px; background-color: #fff; border-left: 4px solid #3498db;">'
        html += '<h3 style="margin-top: 0; color: #2c3e50;">5️⃣ Movimientos Completados</h3>'
        
        try:
            done_moves = self.env['stock.move'].search_count([('state', '=', 'done')])
            html += f'<p>✅ <strong>Movimientos en estado "done":</strong> {done_moves}</p>'
            
            if done_moves == 0:
                html += '<p style="color: #e67e22;">⚠️ No hay movimientos completados en el sistema</p>'
            
            # Verificar movimientos con requisición
            if hasattr(self.env['stock.move'], 'requisition_line_id'):
                req_moves = self.env['stock.move'].search_count([
                    ('requisition_line_id', '!=', False),
                    ('state', '=', 'done')
                ])
                html += f'<p>✅ <strong>Movimientos completados con requisición:</strong> {req_moves}</p>'
                
                if req_moves == 0:
                    html += '<p style="color: #e67e22;">⚠️ No hay movimientos completados asociados a requisiciones</p>'
            
        except Exception as e:
            html += f'<p style="color: #e74c3c;">❌ <strong>ERROR:</strong> {str(e)}</p>'
        
        html += '</div>'
        return html

    def _check_report_data(self):
        """Verifica datos actuales del reporte"""
        html = '<div style="margin: 20px 0; padding: 15px; background-color: #fff; border-left: 4px solid #27ae60;">'
        html += '<h3 style="margin-top: 0; color: #2c3e50;">6️⃣ Datos del Reporte Fill Rate</h3>'
        
        try:
            report_count = self.env['fill.rate.report'].search_count([])
            html += f'<p><strong>Registros en reporte:</strong> {report_count}</p>'
            
            if report_count == 0:
                html += '<p style="color: #e67e22;">⚠️ No hay datos en el reporte</p>'
                html += '<p>💡 Ejecuta "Generar Datos del Reporte" para crear los registros</p>'
            else:
                html += '<p>✅ Hay datos en el reporte</p>'
                
                # Estadísticas básicas
                reports = self.env['fill.rate.report'].search([], limit=100)
                avg_fill_rate = sum(r.fill_rate for r in reports) / len(reports) if reports else 0
                
                html += f'<p><strong>Fill Rate promedio:</strong> {avg_fill_rate:.2f}%</p>'
                
                low_fill = reports.filtered(lambda r: r.fill_rate < 70)
                html += f'<p><strong>Registros con Fill Rate bajo (&lt;70%):</strong> {len(low_fill)}</p>'
                
        except Exception as e:
            html += f'<p style="color: #e74c3c;">❌ <strong>ERROR:</strong> {str(e)}</p>'
        
        html += '</div>'
        return html

    def action_generate_data(self):
        """Genera/actualiza los datos del reporte"""
        try:
            self.env['fill.rate.report'].generate_report_data()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('¡Éxito!'),
                    'message': _('Los datos del reporte Fill Rate han sido generados/actualizados correctamente.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_('Error al generar datos: %s') % str(e))

    def action_clear_data(self):
        """Limpia todos los datos del reporte"""
        try:
            reports = self.env['fill.rate.report'].search([])
            count = len(reports)
            reports.unlink()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Datos Eliminados'),
                    'message': _('Se eliminaron %s registros del reporte.') % count,
                    'type': 'info',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_('Error al eliminar datos: %s') % str(e))
