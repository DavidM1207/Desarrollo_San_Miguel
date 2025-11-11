/** @odoo-module */

import { PartnerDetailsEdit } from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

patch(PartnerDetailsEdit.prototype, {
    
    async saveChanges() {
        console.log("═══════════════════════════════════════");
        console.log("VALIDANDO CLIENTE ANTES DE GUARDAR");
        console.log("═══════════════════════════════════════");
        
        // Obtener los valores actuales del formulario
        const mobile = this.changes.mobile || this.props.partner.mobile || "";
        const phone = this.changes.phone || this.props.partner.phone || "";
        
        console.log("Mobile actual:", mobile);
        console.log("Phone actual:", phone);
        
        // Validar que ambos campos estén llenos
        const errors = [];
        
        if (!mobile || mobile.trim() === "" || !phone || phone.trim()=="") {
            errors.push("• Móvil (Mobile)");
        }
        
         
        // Si hay errores, mostrar mensaje y bloquear guardado
        if (errors.length > 0) {
            console.log("❌ VALIDACIÓN FALLIDA");
            console.log("Campos faltantes:", errors);
            
            await this.popup.add(ErrorPopup, {
                title: _t("⚠️ Campos Obligatorios Faltantes"),
                body: _t(
                    "No puedes guardar el cliente sin completar los siguientes campos:\n\n" +
                    errors.join("\n") + "\n\n" +
                    "Por favor, completa todos los campos obligatorios antes de guardar."
                ),
            });
            
            return; // BLOQUEAR el guardado
        }
        
        console.log("✅ VALIDACIÓN EXITOSA - Guardando cliente");
        console.log("═══════════════════════════════════════");
        
        // Si la validación pasa, continuar con el guardado normal
        return super.saveChanges(...arguments);
    }
});