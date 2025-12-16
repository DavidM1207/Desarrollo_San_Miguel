from odoo import models, fields


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'
    
    store_image = fields.Image(string='Imagen de la tienda', help='Imagen del punto de recolección')
    google_maps_link = fields.Char(string='Link de Google Maps', help='URL de Google Maps para la ubicación de la tienda')
