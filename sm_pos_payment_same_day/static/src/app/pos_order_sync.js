/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

// Patch del PosStore para escuchar notificaciones de aprobación
patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        
        console.log("POS Order Sync - Configurando escucha de notificaciones");
        
        // Acceder al bus service correctamente
        const busService = this.env.services.bus_service;
        
        if (!busService) {
            console.error("Bus service no disponible");
            return;
        }
        
        // Escuchar notificaciones de pagos aprobados
        busService.addEventListener("notification", ({ detail: notifications }) => {
            for (const notification of notifications) {
                if (notification.type === "pos_payment_approved") {
                    console.log("═══════════════════════════════════════");
                    console.log("NOTIFICACIÓN: Pago aprobado recibida");
                    console.log("Payload:", notification.payload);
                    this.handlePaymentApproved(notification.payload);
                }
            }
        });
        
        console.log("✓ Escucha de notificaciones configurada");
    },
    
    /**
     * Manejar la aprobación de un pago
     * @param {Object} payload - Datos del pago aprobado
     */
    handlePaymentApproved(payload) {
        const { pos_order_id, old_payment_method_id, new_payment_method_id, amount } = payload;
        
        console.log("Buscando orden en POS:", pos_order_id);
        
        // Buscar la orden actual
        const currentOrder = this.get_order();
        
        if (!currentOrder || currentOrder.id !== pos_order_id) {
            console.log("No es la orden actual, ignorando notificación");
            return;
        }
        
        console.log("✓ Es la orden actual:", currentOrder.name);
        
        // Actualizar los pagos de la orden
        this.updateOrderPayments(currentOrder, old_payment_method_id, new_payment_method_id, amount);
        
        console.log("═══════════════════════════════════════");
    },
    
    /**
     * Actualizar los pagos de una orden
     */
    updateOrderPayments(order, oldMethodId, newMethodId, amount) {
        console.log("Actualizando pagos de la orden");
        console.log("  Método antiguo ID:", oldMethodId);
        console.log("  Método nuevo ID:", newMethodId);
        console.log("  Monto:", amount);
        
        // Buscar el método de pago nuevo en los métodos disponibles
        const paymentMethods = this.payment_methods;
        const newPaymentMethod = paymentMethods.find((pm) => pm.id === newMethodId);
        
        if (!newPaymentMethod) {
            console.error("Método de pago nuevo no encontrado:", newMethodId);
            return;
        }
        
        console.log("✓ Método de pago nuevo encontrado:", newPaymentMethod.name);
        
        // Obtener las líneas de pago actuales
        const paymentlines = order.get_paymentlines();
        
        console.log("Paymentlines actuales:", paymentlines.length);
        
        // Eliminar paymentlines del método antiguo
        const paymentlinesToRemove = paymentlines.filter(
            (pl) => pl.payment_method && pl.payment_method.id === oldMethodId
        );
        
        console.log("Paymentlines a eliminar:", paymentlinesToRemove.length);
        
        for (const pl of paymentlinesToRemove) {
            console.log("  Eliminando:", pl.payment_method.name, pl.amount);
            order.remove_paymentline(pl);
        }
        
        // Agregar el nuevo paymentline
        console.log("Agregando nuevo paymentline:", newPaymentMethod.name, amount);
        
        const newPaymentline = order.add_paymentline(newPaymentMethod);
        
        if (newPaymentline) {
            newPaymentline.set_amount(amount);
            console.log("✓ Paymentline agregado con monto:", newPaymentline.amount);
        } else {
            console.error("No se pudo agregar el paymentline");
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