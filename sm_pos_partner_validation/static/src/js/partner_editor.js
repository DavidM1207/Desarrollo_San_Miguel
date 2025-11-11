/** @odoo-module */

import { PartnerDetailsEdit } from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

patch(PartnerDetailsEdit.prototype, {
    
    // Lista de números no permitidos
    get invalidPhoneNumbers() {
        return [
            '00000000',
            '11111111',
            '22222222',
            '33333333',
            '44444444',
            '55555555',
            '66666666',
            '77777777',
            '88888888',
            '99999999',
            '12345678',
            '87654321'
        ];
    },
    
    validatePhoneNumber(phoneNumber, fieldName) {
        const errors = [];
        const phone = phoneNumber ? phoneNumber.trim() : "";
        
      
        
        // 1. Verificar que no esté vacío (OBLIGATORIO)
        if (!phone || phone === "") {
            errors.push(`${fieldName} es OBLIGATORIO y no puede estar vacío`);
            return errors; // Si está vacío, no validar lo demás
        }
        
        // 2. Verificar que solo contenga números
        if (!/^\d+$/.test(phone)) {
            errors.push(`${fieldName} debe contener solo números (sin espacios, guiones o caracteres especiales)`);
        }
        
        // 3. Verificar que tenga exactamente 8 dígitos
        if (phone.length !== 8) {
            errors.push(`${fieldName} debe tener exactamente 8 dígitos (actualmente tiene ${phone.length})`);
        }
        
        // 4. Verificar que no sea un número de la lista prohibida
        if (this.invalidPhoneNumbers.includes(phone)) {
            errors.push(`${fieldName} no puede ser ${phone} (número no válido)`);
        }
        
        return errors;
    },
    
    async saveChanges() {
       
        
        // Obtener los valores actuales del formulario
        const mobile = this.changes.mobile || this.props.partner.mobile || "";
        const phone = this.changes.phone || this.props.partner.phone || "";
        
        
        const allErrors = [];
        
        // VALIDAR MOBILE (OBLIGATORIO)
        
        const mobileErrors = this.validatePhoneNumber(mobile, "Móvil");
        if (mobileErrors.length > 0) {
            allErrors.push("\n MÓVIL:");
            mobileErrors.forEach(error => allErrors.push(`   • ${error}`));
        }
        
        // VALIDAR PHONE (OBLIGATORIO)
        
        const phoneErrors = this.validatePhoneNumber(phone, "Teléfono");
        if (phoneErrors.length > 0) {
            allErrors.push("\n TELÉFONO:");
            phoneErrors.forEach(error => allErrors.push(`   • ${error}`));
        }
        
        // Si hay errores en cualquiera de los dos campos, BLOQUEAR
        if (allErrors.length > 0) {
            
            allErrors.forEach(error => console.log(error));
      
            
            await this.popup.add(ErrorPopup, {
                title: _t("Error en Validación de Cliente"),
                body: _t(
                    "AMBOS CAMPOS SON OBLIGATORIOS\n\n" +
                    "No se puede guardar el cliente. Corrige los siguientes errores:\n" +
                    allErrors.join("\n") + "\n\n" +
                    "═══════════════════════════════\n" +
                    "REQUISITOS:\n" +
                    "✓ Móvil y Teléfono son OBLIGATORIOS (ambos)\n" +
                    "✓ Solo números (sin espacios ni guiones)\n" +
                    "✓ Exactamente 8 dígitos cada uno\n" +
                    "✓ No repeticiones (00000000, 11111111, etc.)\n" +
                    "✓ No secuencias (12345678, 87654321)"
                ),
            });
            
            return; // BLOQUEAR el guardado
        }
        
       
        
        // Si ambos campos son válidos, continuar con el guardado
        return super.saveChanges(...arguments);
    }
});