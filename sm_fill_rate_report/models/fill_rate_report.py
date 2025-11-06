# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FillRateReport(models.Model):
    _name = 'fill.rate.report'
    _description = 'Reporte Fill Rate de Requisiciones'
    _order = 'create_date desc, requisition_id desc'
    _rec_name = 'requisition_id'

    requisition_id = fields.Many2one(
        'employee.purchase.requisition',
        string='Requisición',
        required=True,
        readonly=True,
        ondelete='cascade'
    )
    requisition_line_id = fields.Many2one(
        'requisition.order',  # Modelo exacto de las líneas de requisición
        string='Línea de Requisición',
        required=True,
        readonly=True,
        ondelete='cascade'
    )
    create_date = fields.Datetime(
        string='Fecha Creación',
        related='requisition_id.create_date',
        store=True,
        readonly=True
    )
    requisition_number = fields.Char(
        string='Número Requisición',
        related='requisition_id.name',
        store=True,
        readonly=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        readonly=True
    )
    product_name = fields.Char(
        string='Nombre Producto',
        related='product_id.display_name',
        store=True,
        readonly=True
    )
    demand = fields.Float(
        string='Demanda',
        readonly=True,
        digits='Product Unit of Measure'
    )
    qty_original = fields.Float(
        string='Cantidad Original (Solicitada)',
        readonly=True,
        digits='Product Unit of Measure'
    )
    qty_delivered = fields.Float(
        string='Cantidad Entregada',
        readonly=True,
        digits='Product Unit of Measure'
    )
    fill_rate = fields.Float(
        string='Fill Rate (%)',
        compute='_compute_fill_rate',
        store=True,
        readonly=True,
        digits=(16, 2)
    )
    state = fields.Selection(
        related='requisition_id.state',
        string='Estado',
        store=True,
        readonly=True
    )
    requisition_type = fields.Selection([
        ('purchase_order', 'Orden de Compra'),
        ('internal_transfer', 'Transferencia Interna'),
    ], string='Tipo', readonly=True)

    @api.depends('qty_original', 'qty_delivered')
    def _compute_fill_rate(self):
        """Calcula el Fill Rate como porcentaje de entrega"""
        for record in self:
            if record.qty_original and record.qty_original > 0:
                record.fill_rate = (record.qty_delivered / record.qty_original) * 100
            else:
                record.fill_rate = 0.0

    @api.model
    def generate_report_data(self):
        """
        Genera/actualiza los datos del reporte Fill Rate
        Este método se puede llamar manualmente o programar con un cron
        """
        # Limpiar datos anteriores (opcional, dependiendo de si quieres mantener histórico)
        # self.search([]).unlink()

        # Buscar todas las requisiciones de tipo transferencia interna
        requisitions = self.env['employee.purchase.requisition'].search([])
        
        data_to_create = []
        existing_records = {}
        
        # Cargar registros existentes para actualizarlos
        existing = self.search([])
        for rec in existing:
            key = (rec.requisition_id.id, rec.requisition_line_id.id)
            existing_records[key] = rec

        for requisition in requisitions:
            for line in requisition.requisition_order_ids:
                # Filtrar solo transferencias internas
                if line.requisition_type != 'internal_transfer':
                    continue
                
                # Calcular cantidad entregada desde stock moves
                qty_delivered = self._get_delivered_quantity(requisition, line)
                
                # Datos del registro
                data = {
                    'requisition_id': requisition.id,
                    'requisition_line_id': line.id,
                    'product_id': line.product_id.id,
                    'demand': line.demand if hasattr(line, 'demand') else line.qty,
                    'qty_original': line.qty,
                    'qty_delivered': qty_delivered,
                    'requisition_type': line.requisition_type,  # Guardar el tipo manualmente
                }
                
                # Verificar si ya existe el registro
                key = (requisition.id, line.id)
                if key in existing_records:
                    # Actualizar registro existente
                    existing_records[key].write(data)
                else:
                    # Crear nuevo registro
                    data_to_create.append(data)

        # Crear nuevos registros en batch
        if data_to_create:
            self.create(data_to_create)

        return True

    def _get_delivered_quantity(self, requisition, requisition_line):
        """
        Calcula la cantidad entregada basándose en los movimientos de inventario
        La relación es: requisition.name == stock.move.requisition_order
        Solo cuenta movimientos del DESTINO FINAL (transit → internal) completados
        """
        qty_delivered = 0.0
        
        # Buscar movimientos de stock asociados a esta requisición y producto
        # La relación es por string: requisition.name == move.requisition_order
        stock_moves = self.env['stock.move'].search([
            ('requisition_order', '=', requisition.name),
            ('product_id', '=', requisition_line.product_id.id),
            ('state', '=', 'done'),  # Solo movimientos completados
            # Solo contar el movimiento final (transit → internal)
            ('picking_id.location_id.usage', '=', 'transit'),
            ('picking_id.location_dest_id.usage', '=', 'internal'),
        ])
        
        # Sumar las cantidades de los movimientos completados
        for move in stock_moves:
            # Usar quantity que es la cantidad realmente procesada
            qty_delivered += move.quantity if hasattr(move, 'quantity') else move.product_uom_qty
        
        return qty_delivered

    @api.model
    def action_refresh_report(self):
        """Acción para refrescar los datos del reporte"""
        self.generate_report_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Actualizado'),
                'message': _('El reporte Fill Rate ha sido actualizado exitosamente.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_requisition(self):
        """Acción para ver la requisición desde el reporte"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Requisición'),
            'res_model': 'employee.purchase.requisition',
            'res_id': self.requisition_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_stock_moves(self):
        """Acción para ver los movimientos de stock asociados"""
        self.ensure_one()
        
        stock_moves = self.env['stock.move'].search([
            ('requisition_order', '=', self.requisition_id.name),
            ('product_id', '=', self.product_id.id),
        ])
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Movimientos de Inventario'),
            'res_model': 'stock.move',
            'domain': [('id', 'in', stock_moves.ids)],
            'view_mode': 'tree,form',
            'target': 'current',
        }
