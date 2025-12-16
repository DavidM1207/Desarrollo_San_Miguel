from odoo import models, fields, api


class Website(models.Model):
    _inherit = 'website'

    skip_payment_step = fields.Boolean(string='Omitir el paso de pago', default=False)
    skip_payment_message = fields.Text(string='Mensaje de omitir pago', default='En breve nos comunicaremos con usted.', translate=True)
    helpdesk_team_id = fields.Many2one('helpdesk.team', string='Equipo de Helpdesk', help='Equipo de helpdesk donde se crearán los tickets de órdenes confirmadas')
    helpdesk_notify_customer = fields.Boolean(string='Notificar al cliente sobre el ticket', default=False, help='Si está activado, el cliente recibirá un correo cuando se cree el ticket de helpdesk')

    def _get_checkout_steps(self, *args, **kwargs):
        steps = super()._get_checkout_steps(*args, **kwargs)
        if self.skip_payment_step:
            for step in steps:
                try:
                    # Manejar diferentes estructuras de steps
                    if isinstance(step, (list, tuple)) and len(step) > 1:
                        if isinstance(step[1], dict):
                            # Estructura: [valor, {'name': 'Payment', ...}]
                            step_name = step[1].get('name')
                        else:
                            # Estructura: [valor, 'Payment']
                            step_name = step[1]
                    else:
                        # Estructura simple: ['Payment']
                        step_name = step[0] if isinstance(step, (list, tuple)) else step
                    
                    # Convertir a string para comparación
                    if hasattr(step_name, '__str__'):
                        step_name_str = str(step_name)
                    else:
                        step_name_str = str(step_name)
                    
                    # Verificar si es el paso de Payment
                    if 'Payment' in step_name_str or step_name_str == 'Payment':
                        # Modificar el nombre según la estructura
                        if isinstance(step, (list, tuple)) and len(step) > 1 and isinstance(step[1], dict):
                            step[1]['name'] = 'Finalizar'
                        elif isinstance(step, (list, tuple)) and len(step) > 1:
                            step[1] = 'Finalizar'
                        else:
                            if isinstance(step, (list, tuple)):
                                step[0] = 'Finalizar'
                            else:
                                step = 'Finalizar'
                except (IndexError, TypeError, AttributeError):
                    # Si hay error en la estructura, continuar con el siguiente step
                    continue
        return steps
