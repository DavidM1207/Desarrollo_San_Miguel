from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class MrpCustomFabric(models.TransientModel):
    _name = 'mrp.custom.fabric'
    _description = 'Custom Fabric Wizard'

    product_id = fields.Many2one('product.product', string='Materia Prima (Troza)', required=True)
    quantity = fields.Float(string='Cantidad de Trozas', required=True, default=1.0)
    pie_tablar_mp = fields.Float(string='Pie Tablar MP', compute='_compute_pie_tablar_mp', store=True, readonly=True)
    fabric_lines = fields.One2many('mrp.custom.fabric.lines', 'fabric_id', string='Productos a Fabricar')
    total_percent = fields.Float(string='Total %', compute='_compute_total_percent', store=False)
    total_pie_tablar_usado = fields.Float(string='Total Pie Tablar Usado', compute='_compute_total_pie_tablar', store=False)
    pie_tablar_disponible = fields.Float(string='Pie Tablar Disponible', compute='_compute_pie_tablar_disponible', store=False)
    date = fields.Datetime(string='Fecha', default=fields.Datetime.now)

    @api.depends('product_id', 'quantity', 'product_id.pie_tablar')
    def _compute_pie_tablar_mp(self):
        """Calcular pie tablar total de la materia prima"""
        for record in self:
            if record.product_id and record.quantity > 0:
                record.pie_tablar_mp = record.product_id.pie_tablar * record.quantity
            else:
                record.pie_tablar_mp = 0.0

    @api.depends('fabric_lines.pie_tablar_consumido')
    def _compute_total_percent(self):
        """Calcular porcentaje total usado basado en pie tablar"""
        for record in self:
            if record.pie_tablar_mp > 0:
                total_usado = sum(record.fabric_lines.mapped('pie_tablar_consumido'))
                record.total_percent = (total_usado / record.pie_tablar_mp) * 100.0
            else:
                record.total_percent = 0.0

    @api.depends('fabric_lines.pie_tablar_consumido')
    def _compute_total_pie_tablar(self):
        """Calcular total de pie tablar usado"""
        for record in self:
            record.total_pie_tablar_usado = sum(record.fabric_lines.mapped('pie_tablar_consumido'))

    @api.depends('pie_tablar_mp', 'total_pie_tablar_usado')
    def _compute_pie_tablar_disponible(self):
        """Calcular pie tablar disponible"""
        for record in self:
            record.pie_tablar_disponible = record.pie_tablar_mp - record.total_pie_tablar_usado

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            # Validar que la materia prima tenga pie tablar configurado
            if not self.product_id.pie_tablar or self.product_id.pie_tablar <= 0:
                return {
                    'warning': {
                        'title': _('Advertencia'),
                        'message': _('El producto seleccionado no tiene configurado el campo "Pie Tablar" o es cero.\n\n'
                                   'Por favor configure este valor en el producto antes de continuar.')
                    }
                }
            self.fabric_lines = [(5, 0, 0)]

    @api.onchange('quantity')
    def _onchange_quantity(self):
        """Recalcular cuando cambia la cantidad de materia prima"""
        if self.quantity <= 0:
            return {
                'warning': {
                    'title': _('Advertencia'),
                    'message': _('La cantidad de materia prima debe ser mayor a cero.')
                }
            }

    @api.onchange('fabric_lines')
    def _onchange_fabric_lines(self):
        if self.fabric_lines:
            for line in self.fabric_lines:
                if not line.date:
                    line.date = self.date

    @api.onchange('date')
    def _onchange_date(self):
        if self.date:
            for line in self.fabric_lines:
                if not line.date:
                    line.date = self.date

    def create_productions(self):
        """Crear órdenes de fabricación para cada línea"""
        if not self.fabric_lines:
            raise UserError(_('Debe agregar al menos un producto a fabricar.'))
        
        # Validar que no se supere el 100% de pie tablar disponible
        if self.total_percent > 100:
            raise UserError(_(
                'El total de Pie Tablar asignado (%.2f%%) supera el 100%% disponible.\n\n'
                'Pie Tablar total disponible: %.2f\n'
                'Pie Tablar usado: %.2f\n'
                'Pie Tablar excedente: %.2f\n\n'
                'Por favor ajuste las cantidades antes de crear las órdenes de fabricación.'
            ) % (
                self.total_percent,
                self.pie_tablar_mp,
                self.total_pie_tablar_usado,
                self.total_pie_tablar_usado - self.pie_tablar_mp
            ))
        
        productions = []
        for line in self.fabric_lines:
            if line.product_id and line.quantity_to_produce > 0:
                # Buscar una BoM existente para el producto (opcional)
                bom = self.env['mrp.bom'].search([
                    '|',
                    ('product_id', '=', line.product_id.id),
                    '&',
                    ('product_id', '=', False),
                    ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id),
                    ('type', '=', 'normal'),
                    ('company_id', 'in', [self.env.company.id, False])
                ], limit=1)
                
                production_vals = {
                    'product_id': line.product_id.id,
                    'product_qty': line.quantity_to_produce,
                    'product_uom_id': line.product_id.uom_id.id,
                    'date_start': line.date or self.date,
                }
                
                # Si existe BoM, la asignamos
                if bom:
                    production_vals['bom_id'] = bom.id
                
                production = self.env['mrp.production'].create(production_vals)
                
                # Si no hay BoM, agregamos manualmente el componente (materia prima)
                if not bom:
                    production.write({
                        'move_raw_ids': [(0, 0, {
                            'name': self.product_id.name,
                            'product_id': self.product_id.id,
                            'product_uom_qty': line.consu_quan,
                            'product_uom': self.product_id.uom_id.id,
                            'location_id': production.location_src_id.id,
                            'location_dest_id': production.product_id.property_stock_production.id,
                        })]
                    })
                
                productions.append(production.id)
        
        if productions:
            return {
                'name': _('Órdenes de Fabricación Creadas'),
                'type': 'ir.actions.act_window',
                'res_model': 'mrp.production',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', productions)],
                'target': 'current',
            }
        
        return {'type': 'ir.actions.act_window_close'}


class MrpCustomFabricLines(models.TransientModel):
    _name = 'mrp.custom.fabric.lines'
    _description = 'Custom Fabric Lines Wizard'

    fabric_id = fields.Many2one('mrp.custom.fabric', string='Fabric Wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Producto a Fabricar', required=True)
    pie_tablar_producto = fields.Float(string='Pie Tablar Unitario', related='product_id.pie_tablar', readonly=True)
    quantity_to_produce = fields.Float(string='Unidades a Producir', required=True, default=1.0)
    pie_tablar_consumido = fields.Float(string='Pie Tablar Consumido', compute='_compute_pie_tablar_consumido', store=True, readonly=True)
    porcent = fields.Float(string='% Uso', compute='_compute_porcent', store=True, readonly=True)
    consu_quan = fields.Float(string='Trozas a Usar', compute='_compute_consu_quan', store=True, readonly=True)
    date = fields.Datetime(string='Fecha')

    @api.depends('product_id', 'quantity_to_produce', 'product_id.pie_tablar')
    def _compute_pie_tablar_consumido(self):
        """Calcular pie tablar consumido = pie_tablar_unitario * unidades_a_producir"""
        for record in self:
            if record.product_id and record.quantity_to_produce > 0:
                record.pie_tablar_consumido = record.product_id.pie_tablar * record.quantity_to_produce
            else:
                record.pie_tablar_consumido = 0.0

    @api.depends('pie_tablar_consumido', 'fabric_id.pie_tablar_mp')
    def _compute_porcent(self):
        """Calcular porcentaje: (Pie Tablar Consumido / Pie Tablar Total MP) × 100"""
        for record in self:
            total_pie_tablar = record.fabric_id.pie_tablar_mp or 0.0
            if record.pie_tablar_consumido > 0.0 and total_pie_tablar > 0.0:
                record.porcent = (record.pie_tablar_consumido / total_pie_tablar) * 100.0
            else:
                record.porcent = 0.0

    @api.depends('porcent', 'fabric_id.quantity')
    def _compute_consu_quan(self):
        """Calcular trozas a usar: (% Uso / 100) × Cantidad de Trozas del encabezado"""
        for record in self:
            cantidad_trozas = record.fabric_id.quantity or 0.0
            if record.porcent > 0.0 and cantidad_trozas > 0.0:
                record.consu_quan = (record.porcent / 100.0) * cantidad_trozas
            else:
                record.consu_quan = 0.0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Validar que el producto tenga pie tablar configurado"""
        if self.product_id:
            if not self.product_id.pie_tablar or self.product_id.pie_tablar <= 0:
                return {
                    'warning': {
                        'title': _('Advertencia'),
                        'message': _('El producto "%s" no tiene configurado el campo "Pie Tablar" o es cero.\n\n'
                                   'Por favor configure este valor en el producto antes de continuar.') % self.product_id.name
                    }
                }

    @api.onchange('quantity_to_produce')
    def _onchange_quantity_to_produce(self):
        """Validar que no se supere el pie tablar disponible"""
        # Solo validar si hay valores válidos
        if not (self.quantity_to_produce > 0 and self.product_id and self.fabric_id.pie_tablar_mp > 0):
            return
        
        # Calcular pie tablar que consumiría esta línea
        pie_tablar_necesario = self.product_id.pie_tablar * self.quantity_to_produce
        
        # Calcular total consumido por otras líneas (excluyendo esta)
        otras_lineas = self.fabric_id.fabric_lines.filtered(lambda l: l.id != self.id and l.id)
        total_otras = sum(otras_lineas.mapped('pie_tablar_consumido'))
        
        # Calcular cuánto quedaría disponible después de agregar esta línea
        pie_tablar_disponible_despues = self.fabric_id.pie_tablar_mp - total_otras - pie_tablar_necesario
        
        # Solo mostrar advertencia si realmente se excede (queda negativo)
        if pie_tablar_disponible_despues < -0.01:  # Margen de error por decimales
            return {
                'warning': {
                    'title': _('Sin Pie Tablar Disponible'),
                    'message': _('No hay suficiente Pie Tablar. Ya se ha consumido todo el material disponible.')
                }
            }

    @api.onchange('date')
    def _onchange_date(self):
        if self.fabric_id.date and not self.date:
            self.date = self.fabric_id.date

    @api.constrains('quantity_to_produce')
    def _check_quantity_to_produce(self):
        """Validación: cantidad debe ser positiva"""
        for record in self:
            if record.quantity_to_produce < 0:
                raise ValidationError(_('La cantidad a producir no puede ser negativa.'))