# -*- coding: utf-8 -*-
from odoo import api, models, _
from odoo.exceptions import ValidationError

try:
    from odoo.http import request
except Exception:
    request = None

class ResPartner(models.Model):
    _inherit = "res.partner"

    # ---------- Helpers ----------
    def _is_pos_request(self):
        """Detecta si la creación/edición viene desde la UI del POS.
        - Contexto incluye pos_session_id (estándar POS) o is_pos_ui
        - O heurística por referrer/path que contenga '#pos', '/pos/', 'point_of_sale' o 'pos/web'
        """
        ctx = self.env.context or {}
        if ctx.get("pos_session_id") or ctx.get("is_pos_ui"):
            return True
        try:
            if request and getattr(request, "httprequest", None):
                ref = (request.httprequest.referrer or "") + " " + (request.httprequest.path or "")
                ref = ref.lower()
                if "#pos" in ref or "/pos/" in ref or "point_of_sale" in ref or "pos/web" in ref:
                    return True
        except Exception:
            pass
        return False

    def _require_phone_8digits(self, value, label):
        s = (value or "").strip()
        if not s:
            raise ValidationError(_("En POS, %s es obligatorio.") % label)
        # Solo números (sin letras ni caracteres especiales) y exactamente 8 dígitos
        if not s.isdigit():
            raise ValidationError(_("En POS, %s debe contener solo números (8 dígitos).") % label)
        if len(s) != 8:
            raise ValidationError(_("En POS, %s debe tener exactamente 8 dígitos.") % label)
        if s == "11111111":
            raise ValidationError(_("En POS, %s debe ser un número correcto.") % label)
        if s == "22222222":
            raise ValidationError(_("En POS, %s debe ser un número correcto.") % label)
        if s == "00000000":
            raise ValidationError(_("En POS, %s debe ser un número correcto.") % label)
        if s == "33333333":
            raise ValidationError(_("En POS, %s debe ser un número correcto.") % label)
        if s == "44444444":
            raise ValidationError(_("En POS, %s debe ser un número correcto.") % label)
        if s == "55555555":
            raise ValidationError(_("En POS, %s debe ser un número correcto.") % label)
        if s == "66666666":
            raise ValidationError(_("En POS, %s debe ser un número correcto.") % label)
        if s == "77777777":
            raise ValidationError(_("En POS, %s debe ser un número correcto.") % label)
        if s == "88888888":
            raise ValidationError(_("En POS, %s debe ser un número correcto.") % label)
        if s == "99999999":
            raise ValidationError(_("En POS, %s debe ser un número correcto.") % label)
        if s == "12345678":
            raise ValidationError(_("En POS, %s debe ser un número correcto.") % label)
        if s == "87654321":
            raise ValidationError(_("En POS, %s debe ser un número correcto.") % label)



        # ---------- Overrides ----------
    @api.model_create_multi
    def create(self, vals_list):
        if self._is_pos_request():
            for vals in vals_list:
                
              
                self._require_phone_8digits(vals.get("phone"), _("Teléfono"))
                self._require_phone_8digits(vals.get("mobile"), _("Móvil"))
        return super().create(vals_list)

    def write(self, vals):
        if self._is_pos_request():
            for partner in self:
                
               
                phone_final = vals.get("phone", partner.phone)
                mobile_final = vals.get("mobile", partner.mobile)
                self._require_phone_8digits(phone_final, _("Teléfono"))
                self._require_phone_8digits(mobile_final, _("Móvil"))
        return super().write(vals)
