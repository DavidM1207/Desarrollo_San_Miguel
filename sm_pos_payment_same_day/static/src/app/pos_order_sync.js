/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

// Patch del PosStore para escuchar notificaciones de aprobación
patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        
        // Escuchar notificaciones de pagos aprobados
        this.busService.subscribe("pos_payment_approved", (payload) => {
            console.log("═══════════════════════════════════════");
            console.log("NOTIFICACIÓN: Pago aprobado recibida");
            console.log("Payload:", payload);
            this.handlePaymentApproved(payload);
        });
    },
    
    /**
     * Manejar la aprobación de un pago
     * @param {Object} payload - Datos del pago aprobado
     */
    handlePaymentApproved(payload) {
        const { pos_order_id, old_payment_method_id, new_payment_method_id, amount } = payload;
        
        console.log("Buscando orden en POS:", pos_order_id);
        
        // Buscar la orden en las órdenes cargadas
        const order = this.models["pos.order"].find((o) => o.id === pos_order_id);
        
        if (!order) {
            console.log("Orden no encontrada en POS, puede estar en otra sesión");
            return;
        }
        
        console.log("✓ Orden encontrada:", order.pos_reference);
        
        // Si es la orden actual, actualizarla
        if (this.selectedOrder && this.selectedOrder.id === pos_order_id) {
            console.log("Es la orden actual - actualizando paymentlines");
            this.updateOrderPayments(this.selectedOrder, old_payment_method_id, new_payment_method_id, amount);
        } else {
            console.log("No es la orden actual, pero está cargada");
            // También podríamos actualizar órdenes no seleccionadas si es necesario
        }
        
        console.log("═══════════════════════════════════════");
    },
    
    /**
     * Actualizar los pagos de una orden
     */
    updateOrderPayments(order, oldMethodId, newMethodId, amount) {
        console.log("Actualizando pagos de la orden");
        console.log("  Método antiguo:", oldMethodId);
        console.log("  Método nuevo:", newMethodId);
        console.log("  Monto:", amount);
        
        // Buscar el método de pago nuevo
        const newPaymentMethod = this.models["pos.payment.method"].find(
            (pm) => pm.id === newMethodId
        );
        
        if (!newPaymentMethod) {
            console.error("Método de pago nuevo no encontrado:", newMethodId);
            return;
        }
        
        console.log("✓ Método de pago nuevo encontrado:", newPaymentMethod.name);
        
        // Eliminar paymentlines del método antiguo
        const paymentlinesToRemove = order.payment_ids.filter(
            (pl) => pl.payment_method_id && pl.payment_method_id.id === oldMethodId
        );
        
        console.log("Paymentlines a eliminar:", paymentlinesToRemove.length);
        
        for (const pl of paymentlinesToRemove) {
            console.log("  Eliminando:", pl.payment_method_id.name, pl.amount);
            order.removePaymentline(pl);
        }
        
        // Agregar el nuevo paymentline
        console.log("Agregando nuevo paymentline:", newPaymentMethod.name, amount);
        order.addPaymentline(newPaymentMethod);
        
        // Buscar el paymentline recién agregado y ajustar el monto
        const newPaymentline = order.payment_ids.find(
            (pl) => pl.payment_method_id && pl.payment_method_id.id === newMethodId
        );
        
        if (newPaymentline) {
            newPaymentline.set_amount(amount);
            console.log("✓ Monto ajustado:", newPaymentline.amount);
        }
        
        // Mostrar notificación al usuario
        this.env.services.notification.add(
            "Solicitud de pago aprobada. El método de pago ha sido actualizado.",
            {
                type: "success",
                title: "Pago Aprobado",
            }
        );
        
        console.log("✓ Orden actualizada correctamente");
    },
});