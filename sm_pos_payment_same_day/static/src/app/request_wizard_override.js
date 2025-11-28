/** @odoo-module */

import { RequestWizard } from "@pt_pos_payment_approval/app/request_wizard";
import { patch } from "@web/core/utils/patch";

patch(RequestWizard.prototype, {
    /**
     * Sobrescribir submitRequest para capturar y eliminar pagos antiguos
     */
    async submitRequest() {
        console.log("═══════════════════════════════════════");
        console.log("SUBMIT REQUEST - OVERRIDE");
        console.log("═══════════════════════════════════════");
        
        // Capturar los pagos antiguos ANTES de enviar la solicitud
        const currentOrder = this.pos.get_order();
        const oldPaymentLines = currentOrder ? [...currentOrder.get_paymentlines()] : [];
        
        console.log("Pagos actuales antes de solicitud:", oldPaymentLines.map(p => ({
            id: p.cid,
            method: p.payment_method.name,
            amount: p.amount
        })));
        
        // Llamar al método original para crear la solicitud
        const result = await super.submitRequest(...arguments);
        
        console.log("Resultado de super.submitRequest:", result);
        
        // Si la solicitud se creó exitosamente, guardar los IDs de pagos antiguos
        if (result && result.success && result.request_id) {
            console.log("✓ Solicitud creada exitosamente:", result.request_id);
            
            // Convertir paymentlines a IDs que podamos guardar
            const oldPaymentIds = oldPaymentLines.map(pl => {
                // Si ya tiene ID de backend, usar ese
                if (pl.payment_id) {
                    return pl.payment_id;
                }
                // Si no, usaremos el cid temporal
                return `temp_${pl.cid}`;
            });
            
            console.log("IDs de pagos antiguos a guardar:", oldPaymentIds);
            
            // Guardar esta info en la solicitud para que cuando se apruebe,
            // el backend pueda eliminar los pagos antiguos
            try {
                await this.orm.write(
                    "pos.payment.approval.request",
                    [result.request_id],
                    {
                        edit_detail: `REASON:Cambio desde POS|OLD_PAYMENT_CIDS:${oldPaymentIds.join(',')}`
                    }
                );
                console.log("✓ IDs de pagos antiguos guardados en edit_detail");
            } catch (error) {
                console.error("Error al guardar IDs de pagos antiguos:", error);
            }
        }
        
        console.log("═══════════════════════════════════════");
        return result;
    },
});