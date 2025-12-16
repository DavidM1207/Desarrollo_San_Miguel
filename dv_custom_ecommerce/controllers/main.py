from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.website_sale.controllers.main import WebsiteSale


class PortalSale(CustomerPortal):
    
    def _prepare_homepage_values(self, values):
        values = super(PortalSale, self)._prepare_homepage_values(values)
        values['skip_payment_step'] = request.website.skip_payment_step
        values['skip_payment_message'] = request.website.skip_payment_message
        return values
    
    @http.route(['/my/orders/<int:order_id>'], type='http', auth="user", website=True)
    def portal_order_page(self, order_id, report_type=None, access_token=None, message=False, **kw):
        response = super(PortalSale, self).portal_order_page(
            order_id, report_type=report_type, access_token=access_token, message=message, **kw
        )
        
        if hasattr(response, 'qcontext'):
            response.qcontext['skip_payment_step'] = request.website.skip_payment_step
            response.qcontext['skip_payment_message'] = request.website.skip_payment_message
        
        return response


class WebsiteSaleExtended(WebsiteSale):
    
    def _checkout_form_save(self, mode, checkout, all_values):
        """Override para agregar contexto from_website al crear partners"""
        Partner = request.env['res.partner'].with_context(from_website=True)
        if mode[0] == 'new':
            partner_id = Partner.sudo().with_context(tracking_disable=True).create(checkout).id
        elif mode[0] == 'edit':
            partner_id = int(all_values.get('partner_id', 0))
            if partner_id:
                order = request.website.sale_get_order()
                shippings = Partner.sudo().search([("id", "child_of", order.partner_id.commercial_partner_id.ids)])
                if partner_id not in shippings.mapped('id') and partner_id != order.partner_id.id:
                    from werkzeug.exceptions import Forbidden
                    return Forbidden()
                Partner.browse(partner_id).sudo().write(checkout)
        return partner_id
    
    @http.route(['/shop/payment'], type='http', auth="public", website=True, sitemap=False)
    def shop_payment(self, **post):
        order = request.website.sale_get_order()
        
        # Manejar métodos de entrega (igual que el core)
        if order and not order.only_services and (request.httprequest.method == 'POST' or not order.carrier_id):
            carrier_id = post.get('carrier_id')
            keep_carrier = post.get('keep_carrier', False)
            if keep_carrier:
                keep_carrier = bool(int(keep_carrier))
            if carrier_id:
                carrier_id = int(carrier_id)
            
            order._check_carrier_quotation(force_carrier_id=carrier_id, keep_carrier=keep_carrier)
            if carrier_id:
                return request.redirect("/shop/payment")
        
        # Si skip_payment_step está activo, redirigir al proceso de confirmación
        if request.website.skip_payment_step:
            if order and order.state == 'draft':
                render_values = self._get_shop_payment_values(order, **post)
                render_values['skip_payment_message'] = request.website.skip_payment_message
                
                # Filtrar métodos de pago según delivery_type
                if order.carrier_id and order.carrier_id.delivery_type != 'onsite':
                    providers_sudo = render_values.get('providers_sudo', request.env['payment.provider'].sudo())
                    
                    def is_not_onsite_payment(provider):
                        name_lower = provider.name.lower()
                        code_lower = provider.code.lower() if provider.code else ''
                        return not any(keyword in name_lower or keyword in code_lower 
                                     for keyword in ['sitio', 'tienda', 'local', 'onsite', 'cash', 'efectivo'])
                    
                    compatible_providers = providers_sudo.filtered(is_not_onsite_payment)
                    render_values['providers_sudo'] = compatible_providers
                    
                    payment_methods_sudo = render_values.get('payment_methods_sudo', request.env['payment.method'].sudo())
                    compatible_methods = payment_methods_sudo.filtered(
                        lambda pm: any(p in compatible_providers for p in pm.provider_ids)
                    )
                    render_values['payment_methods_sudo'] = compatible_methods
                
                return request.render('dv_custom_ecommerce.payment_skipped_page', render_values)
        
        # Si no, usar el flujo normal
        return super(WebsiteSaleExtended, self).shop_payment(**post)
    
    @http.route(['/shop/update_payment_methods'], type='json', auth="public", website=True)
    def update_payment_methods(self, carrier_id, **kw):
        """Devuelve los métodos de pago filtrados según el carrier"""
        import logging
        _logger = logging.getLogger(__name__)
        
        order = request.website.sale_get_order()
        if not order or not carrier_id:
            return {'payment_methods_html': ''}
        
        # Actualizar carrier en la orden
        order._check_carrier_quotation(force_carrier_id=int(carrier_id))
        
        # Obtener delivery_type del carrier
        carrier = request.env['delivery.carrier'].sudo().browse(int(carrier_id))
        if not carrier:
            return {'payment_methods_html': ''}
        
        delivery_type = carrier.delivery_type
        _logger.info(f"AJAX - Carrier: {carrier.name}, delivery_type: {delivery_type}")
        
        # Obtener TODOS los providers activos directamente
        providers_sudo = request.env['payment.provider'].sudo().search([
            ('state', '=', 'enabled'),
            ('company_id', '=', order.company_id.id)
        ])
        _logger.info(f"AJAX - Total providers: {len(providers_sudo)}, names: {providers_sudo.mapped('name')}")
        
        # Para delivery a domicilio, excluir pago en sitio
        # Para recolección en tienda, mostrar todos los métodos
        if delivery_type != 'onsite':
            def is_not_onsite_payment(provider):
                name_lower = provider.name.lower()
                code_lower = provider.code.lower() if provider.code else ''
                return not any(keyword in name_lower or keyword in code_lower 
                             for keyword in ['sitio', 'tienda', 'local', 'onsite', 'cash', 'efectivo'])
            
            compatible_providers = providers_sudo.filtered(is_not_onsite_payment)
            _logger.info(f"AJAX - Filtered (NOT onsite): {len(compatible_providers)}, names: {compatible_providers.mapped('name')}")
        else:
            compatible_providers = providers_sudo
            _logger.info(f"AJAX - No filter (onsite): {len(compatible_providers)}, names: {compatible_providers.mapped('name')}")
        
        # Obtener payment methods usando el mismo método que el backend
        payment_methods_sudo = request.env['payment.method'].sudo()._get_compatible_payment_methods(
            compatible_providers.ids,
            order.partner_id.id,
            currency_id=order.currency_id.id,
        )
        _logger.info(f"AJAX - Payment methods: {len(payment_methods_sudo)}, names: {payment_methods_sudo.mapped('name')}")
        
        # Renderizar el HTML de payment methods
        show_tokenize_input_mapping = {p.id: False for p in compatible_providers}
        
        payment_html = request.env['ir.ui.view']._render_template('payment.form', {
            'providers_sudo': compatible_providers,
            'payment_methods_sudo': payment_methods_sudo,
            'tokens_sudo': request.env['payment.token'].sudo(),
            'mode': 'payment',
            'display_submit_button': True,
            'amount': order.amount_total,
            'currency': order.currency_id,
            'partner_id': order.partner_id.id,
            'transaction_route': f'/shop/payment/transaction/{order.id}',
            'landing_route': '/shop/payment/validate',
            'show_tokenize_input_mapping': show_tokenize_input_mapping,
            'fees_by_provider': {},
        })
        
        return {
            'payment_methods_html': payment_html,
            'new_amount_delivery': order.amount_delivery,
            'new_amount_untaxed': order.amount_untaxed,
            'new_amount_tax': order.amount_tax,
            'new_amount_total': order.amount_total,
        }
    
    @http.route(['/shop/confirm_order_skip_payment'], type='http', auth="public", website=True, sitemap=False)
    def confirm_order_skip_payment(self, **post):
        import logging
        _logger = logging.getLogger(__name__)
        
        order = request.website.sale_get_order()
        
        if order and order.state == 'draft' and request.website.skip_payment_step:
            # Obtener payment_method_id del post
            payment_method_id = post.get('payment_method_id')
            _logger.info(f"POST data: {post}")
            _logger.info(f"payment_method_id from POST: {payment_method_id}")
            
            # Mover a estado Cotización Web
            order.action_web_quote()
            
            # Guardar payment_method_id
            if payment_method_id:
                order.sudo().write({'payment_method_id': int(payment_method_id)})
                _logger.info(f"Saved payment_method_id {payment_method_id} to order {order.name}")
            else:
                _logger.warning(f"No payment_method_id in POST data for order {order.name}")
            
            # Crear ticket de helpdesk si está configurado
            ticket_id = None
            if request.website.helpdesk_team_id:
                ticket_id = self._create_helpdesk_ticket(order)
            
            # Limpiar el carrito
            request.website.sale_reset()
            
            # Redirigir a página de confirmación con ticket_id
            return request.redirect('/shop/confirmation/%s?ticket_id=%s' % (order.id, ticket_id or ''))
        
        # Si algo falla, volver al carrito
        return request.redirect('/shop/cart')
    
    def _get_stock_by_location(self, order):
        """Obtener stock por ubicación de los productos en la orden"""
        website = request.website
        warehouses = website.sudo().website_warehouses_ids
        
        if not warehouses:
            return ''
        
        stock_html = '<h4>Disponibilidad por Ubicación:</h4>'
        stock_html += '<table style="width:100%; border-collapse: collapse; font-size: 11px;">'
        stock_html += '<thead><tr style="background-color: #e9ecef;">'
        stock_html += '<th style="border: 1px solid #dee2e6; padding: 6px; text-align: left; font-weight: 600;">Producto</th>'
        stock_html += '<th style="border: 1px solid #dee2e6; padding: 6px; text-align: left; font-weight: 600;">Ubicación</th>'
        stock_html += '<th style="border: 1px solid #dee2e6; padding: 6px; text-align: right; font-weight: 600;">Cantidad</th>'
        stock_html += '</tr></thead><tbody>'
        
        for line in order.order_line:
            if line.product_id.type != 'product':
                continue
            
            first_row = True
            
            for warehouse in warehouses:
                quants = request.env['stock.quant'].sudo().search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id', 'child_of', warehouse.lot_stock_id.id)
                ])
                
                total_qty = sum(max(0, q.quantity - q.reserved_quantity) for q in quants)
                
                if total_qty > 0:
                    stock_html += '<tr>'
                    if first_row:
                        stock_html += f'<td style="border: 1px solid #dee2e6; padding: 6px; font-weight: 600; background-color: #f8f9fa;">{line.product_id.display_name}</td>'
                        first_row = False
                    else:
                        stock_html += '<td style="border: 1px solid #dee2e6; padding: 6px;"></td>'
                    stock_html += f'<td style="border: 1px solid #dee2e6; padding: 6px;">{warehouse.name}</td>'
                    stock_html += f'<td style="border: 1px solid #dee2e6; padding: 6px; text-align: right; font-weight: 600;">{int(total_qty)} {line.product_uom.name}</td>'
                    stock_html += '</tr>'
        
        stock_html += '</tbody></table>'
        return stock_html
    
    def _create_helpdesk_ticket(self, order):
        """Crear ticket de helpdesk con información de la orden"""
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        order_url = f"{base_url}/web#id={order.id}&model=sale.order&view_type=form"
        
        # Info de método de pago
        payment_info = ''
        if order.payment_method_id:
            payment_info = f"""<h4>Método de Pago:</h4>
<p><strong>{order.payment_method_id.name}</strong></p>
"""
            # Si es transferencia y hay comprobante, agregarlo
            if order.transfer_proof:
                payment_info += '<p><em>Comprobante de transferencia adjunto</em></p>'
        
        # Info de método de entrega
        delivery_info = ''
        if order.carrier_id:
            delivery_info = f"""<h4>Método de Entrega:</h4>
<p><strong>{order.carrier_id.name}</strong></p>
"""
            if order.carrier_id.delivery_type == 'onsite' and order.carrier_id.google_maps_link:
                delivery_info += f'<p>Ubicación: <a href="{order.carrier_id.google_maps_link}" target="_blank">Ver en Google Maps</a></p>'
        
        # Construir descripción del ticket
        description = f"""<h3>Orden de Venta: {order.name}</h3>
{payment_info}
{delivery_info}
<h4>Dirección de Envío:</h4>
<ul>
<li><strong>Nombre:</strong> {order.partner_shipping_id.name}</li>
{f'<li><strong>NIT:</strong> {order.partner_shipping_id.vat}</li>' if order.partner_shipping_id.vat else ''}
<li><strong>Dirección:</strong> {order.partner_shipping_id.street or ''}</li>
{f'<li>{order.partner_shipping_id.street2}</li>' if order.partner_shipping_id.street2 else ''}
<li><strong>Ciudad:</strong> {order.partner_shipping_id.city or ''} {order.partner_shipping_id.zip or ''}</li>
{f'<li><strong>Estado:</strong> {order.partner_shipping_id.state_id.name}</li>' if order.partner_shipping_id.state_id else ''}
{f'<li><strong>País:</strong> {order.partner_shipping_id.country_id.name}</li>' if order.partner_shipping_id.country_id else ''}
</ul>

<h4>Productos:</h4>
<table style="width:100%; border-collapse: collapse;">
<tr style="background-color: #f0f0f0;">
<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Producto</th>
<th style="border: 1px solid #ddd; padding: 8px; text-align: center;">Cantidad</th>
<th style="border: 1px solid #ddd; padding: 8px; text-align: right;">Precio</th>
</tr>
{''.join([f'<tr><td style="border: 1px solid #ddd; padding: 8px;">{line.name}</td><td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{int(line.product_uom_qty)}</td><td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{order.currency_id.symbol} {line.price_subtotal:.2f}</td></tr>' for line in order.order_line])}
</table>

<h4>Resumen:</h4>
<ul>
<li><strong>Subtotal:</strong> {order.currency_id.symbol} {order.amount_untaxed:.2f}</li>
<li><strong>Impuestos:</strong> {order.currency_id.symbol} {order.amount_tax:.2f}</li>
<li><strong>Total:</strong> {order.currency_id.symbol} {order.amount_total:.2f}</li>
</ul>

"""
        send = request.website.helpdesk_notify_customer
        # Crear el ticket
        ticket = request.env['helpdesk.ticket'].sudo().create({
            'name': f'Orden de Venta: {order.name}',
            'team_id': request.website.helpdesk_team_id.id,
            'partner_id': order.partner_id.id if send else False,
            'description': description,
            'sale_order_id': order.id,
        })
        
        # Agregar notas en el chatter
        from markupsafe import Markup
        ticket.message_post(
            body=Markup(f'<p>Enlace directo a la orden de venta: <a href="{order_url}" target="_blank">{order.name}</a></p>'),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
        
        # Agregar stock por ubicación
        stock_info = self._get_stock_by_location(order)
        if stock_info:
            ticket.message_post(
                body=Markup(stock_info),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
        
        return ticket.id
    
    @http.route(['/shop/confirmation/<int:order_id>'], type='http', auth="public", website=True, sitemap=False)
    def shop_confirmation_skip_payment(self, order_id, **post):
        order = request.env['sale.order'].sudo().browse(order_id)
        
        if not order.exists():
            return request.redirect('/shop')
        
        ticket_id = post.get('ticket_id')
        
        return request.render('dv_custom_ecommerce.order_confirmed_skip_payment_page', {
            'order': order,
            'skip_payment_message': request.website.skip_payment_message,
            'ticket_id': ticket_id,
        })
    
    @http.route(['/shop/upload_transfer_proof'], type='http', auth="public", website=True, methods=['POST'])
    def upload_transfer_proof(self, order_id, ticket_id, transfer_proof, **post):
        order = request.env['sale.order'].sudo().browse(int(order_id))
        
        if order.exists() and transfer_proof:
            # Leer el archivo UNA SOLA VEZ
            file_content = transfer_proof.read()
            
            # Guardar comprobante en la orden
            order.write({
                'transfer_proof': file_content,
                'transfer_proof_filename': transfer_proof.filename,
            })
            
            # Agregar comprobante al ticket en notas internas
            if ticket_id:
                ticket = request.env['helpdesk.ticket'].sudo().browse(int(ticket_id))
                if ticket.exists():
                    from markupsafe import Markup
                    ticket.message_post(
                        body=Markup('<p>Comprobante de transferencia recibido</p>'),
                        message_type='comment',
                        subtype_xmlid='mail.mt_note',
                        attachments=[(transfer_proof.filename, file_content)],
                    )
        
        return request.redirect(f'/shop/confirmation/{order_id}?ticket_id={ticket_id}&uploaded=1')