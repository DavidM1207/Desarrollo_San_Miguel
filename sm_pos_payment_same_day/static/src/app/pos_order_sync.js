/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        
        console.log("═══════════════════════════════════════");
        console.log("POS Order Sync - Inicializando");
        console.log("═══════════════════════════════════════");
        
        // Escuchar notificaciones del bus
        this.env.services.bus_service.addChannel(this.user.partner_id);
        this.env.services.bus_service.addEventListener("notification", this._onBusNotification.bind(this));
        
        console.log("✓ Listener de notificaciones registrado");
    },
    
    /**
     * Manejar notificaciones del bus
     */
    _onBusNotification({ detail: notifications }) {
        for (const { type, payload } of notifications) {
            if (type === "pos_payment_approved") {
                console.log("═══════════════════════════════════════");
                console.log("📩 NOTIFICACIÓN RECIBIDA: Pago aprobado");
                console.log("Payload:", payload);
                this._handlePaymentApproved(payload);
                console.log("═══════════════════════════════════════");
            }
        }
    },
    
    /**
     * Manejar la aprobación de un pago
     */
    _handlePaymentApproved(payload) {
        const { pos_order_id, old_payment_method_id, new_payment_method_id, amount } = payload;
        
        console.log("Procesando aprobación de pago:");
        console.log("  - Orden ID:", pos_order_id);
        console.log("  - Método antiguo ID:", old_payment_method_id);
        console.log("  - Método nuevo ID:", new_payment_method_id);
        console.log("  - Monto:", amount);
        
        // Obtener la orden actual
        const currentOrder = this.get_order();
        
        if (!currentOrder) {
            console.log("❌ No hay orden actual");
            return;
        }
        
        console.log("Orden actual ID:", currentOrder.id);
        console.log("Orden actual nombre:", currentOrder.name);
        
        // Verificar si es la orden correcta
        if (currentOrder.id !== pos_order_id) {
            console.log("❌ No es la orden actual (IDs no coinciden)");
            console.log("   Orden actual:", currentOrder.id);
            console.log("   Orden notificada:", pos_order_id);
            return;
        }
        
        console.log("✅ Es la orden actual - procediendo a actualizar pagos");
        
        // Buscar el nuevo método de pago
        const newPaymentMethod = this.payment_methods.find(pm => pm.id === new_payment_method_id);
        
        if (!newPaymentMethod) {
            console.error("❌ Método de pago nuevo no encontrado:", new_payment_method_id);
            return;
        }
        
        console.log("✓ Método de pago nuevo encontrado:", newPaymentMethod.name);
        
        // Obtener líneas de pago actuales
        const paymentlines = currentOrder.get_paymentlines();
        console.log("Paymentlines actuales:", paymentlines.length);
        
        // Buscar y eliminar líneas con el método antiguo
        let paymentlinesRemoved = 0;
        for (const pl of paymentlines) {
            if (pl.payment_method && pl.payment_method.id === old_payment_method_id) {
                console.log("  Eliminando paymentline:", pl.payment_method.name, pl.amount);
                currentOrder.remove_paymentline(pl);
                paymentlinesRemoved++;
            }
        }
        
        console.log("✓ Paymentlines eliminadas:", paymentlinesRemoved);
        
        // Agregar nuevo paymentline
        console.log("Agregando nuevo paymentline:", newPaymentMethod.name);
        const newPaymentline = currentOrder.add_paymentline(newPaymentMethod);
        
        if (newPaymentline) {
            newPaymentline.set_amount(amount);
            console.log("✓ Paymentline agregada con monto:", newPaymentline.amount);
        } else {
            console.error("❌ Error al agregar paymentline");
            return;
        }
        
        // Mostrar notificación de éxito
        this.env.services.notification.add(
            "✅ Solicitud de pago aprobada. El método de pago ha sido actualizado a: " + newPaymentMethod.name,
            {
                type: "success",
                title: "Pago Aprobado",
                sticky: false,
            }
        );
        
        console.log("✅ Método de pago actualizado exitosamente en el POS");
    },
});