# employee_purchase_fill_rate/models/purchase_order_fill_rate.py
from odoo import models, fields, api


class PurchaseOrderFillRate(models.Model):
    """
    Extiende las 'líneas' de la requisición (según tu comentario: modelo purchase_order).
    Si en tu sistema las líneas son otro modelo (ej. 'purchase.order.line'),
    cambia el _inherit a ese nombre.
    """
    _inherit = 'purchase.order'  # AJUSTA si tus líneas están en otro modelo

    # ---------------------------------------------------------------------
    # Campos relacionados a la cabecera de requisición
    # ---------------------------------------------------------------------
    # OJO: este código asume que en purchase.order tienes un Many2one:
    # requisition_id = fields.Many2one('employee_purchase_requisition', ...)
    # Si el campo se llama distinto, CAMBIA 'requisition_id' en todo el código.
    requisition_create_date = fields.Datetime(
        string="Fecha creación",
        related="requisition_id.create_date",
        store=False,
    )

    requisition_name = fields.Char(
        string="Número Requisición",
        related="requisition_id.name",
        store=False,
    )

    # ---------------------------------------------------------------------
    # Cantidades y Fill Rate
    # ---------------------------------------------------------------------
    # Asumimos que en la línea existe 'product_qty' como cantidad solicitada.
    # Si se llama distinto (ej. 'quantity'), cámbialo en 'demanda' y 'qty_original'.
    demanda = fields.Float(
        string="Demanda (Uds. solicitadas)",
        related="product_qty",
        store=False,
    )

    qty_original = fields.Float(
        string="Cantidad Original (Uds. solicitadas)",
        related="product_qty",
        store=False,
    )

    qty_delivered = fields.Float(
        string="Cantidad Demanda (Uds. entregadas)",
        compute="_compute_fill_rate",
        store=False,
    )

    fill_rate = fields.Float(
        string="Fill Rate (%)",
        compute="_compute_fill_rate",
        digits=(16, 2),
        store=False,
    )

    # Opcional: mostrar unidad de medida en el reporte
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="UdM",
        related="product_uom",  # AJUSTA si tu campo se llama distinto
        store=False,
    )

    # ---------------------------------------------------------------------
    # Cálculo dinámico (solo Python/ORM, sin SQL)
    # ---------------------------------------------------------------------
    @api.depends('product_id', 'product_qty', 'requisition_id')
    def _compute_fill_rate(self):
        """
        Calcula:
        - qty_delivered: suma de cantidades REALMENTE recepcionadas
          desde stock.move en estado 'done', tipo transferencia interna,
          y asociadas a la requisición.
        - fill_rate: (entregadas / solicitadas) * 100

        NOTA:
        - Aquí usamos stock.move, pero podrías cambiar a stock.move.line
          si en tu implementación el qty_done está ahí.
        """
        StockMove = self.env['stock.move']

        for line in self:
            delivered = 0.0

            # Solo calculamos si hay datos mínimos
            if line.requisition_id and line.product_id and line.product_qty:
                # ------------------------------------------------------------------
                # IMPORTANTE: RELACIÓN ENTRE stock.move Y employee_purchase_requisition
                # ------------------------------------------------------------------
                # Aquí asumo que en stock.move tienes un Many2one:
                # employee_purchase_requisition_id = fields.Many2one(
                #     'employee_purchase_requisition', ...
                # )
                #
                # Si tu campo se llama distinto (por ejemplo 'requisition_id'),
                # CAMBIA la línea:
                #   ('employee_purchase_requisition_id', '=', line.requisition_id.id),
                # por el nombre real del campo.
                # ------------------------------------------------------------------

                move_domain = [
                    ('state', '=', 'done'),
                    ('picking_type_id.code', '=', 'internal'),  # Solo transferencias internas
                    ('product_id', '=', line.product_id.id),
                    ('employee_purchase_requisition_id', '=', line.requisition_id.id),
                    # Solo el movimiento de recepción final:
                    # destino en ubicación interna (no la ubicación virtual/transito)
                    ('location_dest_id.usage', '=', 'internal'),
                ]

                moves = StockMove.search(move_domain)

                # En Odoo 17, la cantidad realmente movida está en quantity_done
                delivered = sum(moves.mapped('quantity_done'))

            line.qty_delivered = delivered

            if line.product_qty:
                # Fill Rate lógico: entregadas / solicitadas * 100
                line.fill_rate = (delivered / line.product_qty) * 100.0
            else:
                line.fill_rate = 0.0
