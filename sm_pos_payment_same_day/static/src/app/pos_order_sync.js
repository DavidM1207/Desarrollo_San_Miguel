/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        
        console.log("🔵 POS Order Sync - Modo: Solo notificación");
        
        try {
            const partnerId = this.user?.partner_id;
            
            if (partnerId) {
                this.env.services.bus_service.addChannel(partnerId);
                console.log("✅ Canal agregado");
            }
            
            this.env.services.bus_service.addEventListener("notification", (event) => {
                this._onBusNotification(event);
            });
            
            console.log("✅ Listener registrado");
            
        } catch (error) {
            console.error("❌ ERROR:", error);
        }
    },
    
    _onBusNotification(event) {
        if (!event?.detail) return;
        
        for (const { type, payload } of event.detail) {
            if (type === "pos_payment_approved") {
                console.log("🎯 PAGO APROBADO");
                this._handlePaymentApproved(payload);
            }
        }
    },
    
    _handlePaymentApproved(payload) {
        console.log("\n╔═══════════════════════════════════════╗");
        console.log("║  🎯 PAGO APROBADO - NOTIFICACIÓN      ║");
        console.log("╚═══════════════════════════════════════╝");
        
        const { pos_reference, new_payment_method_id, amount } = payload;
        
        console.log("Orden:", pos_reference);
        
        // Buscar orden
        const allOrders = this.get_order_list();
        let targetOrder = null;
        
        for (const order of allOrders) {
            if (order.name === pos_reference) {
                targetOrder = order;
                break;
            }
        }
        
        if (!targetOrder) {
            console.log("❌ Orden no encontrada en el POS");
            return;
        }
        
        console.log("✅ Orden encontrada:", targetOrder.name);
        
        // Buscar método nuevo (solo para mostrar nombre)
        const newMethod = this.payment_methods.find(pm => pm.id === new_payment_method_id);
        const methodName = newMethod ? newMethod.name : "Método desconocido";
        
        // SOLO NOTIFICACIÓN - El backend ya hizo el cambio
        this.env.services.notification.add(
            `✅ Pago aprobado para "${targetOrder.name}"\n\n` +
            `Método: ${methodName}\n` +
            `Monto: ${amount}\n\n` +
            `💡 Cierra y vuelve a abrir la orden para ver los cambios.`,
            { 
                type: "success", 
                title: "Solicitud Aprobada",
                sticky: true  // Queda visible
            }
        );
        
        console.log("✅ Notificación mostrada");
        console.log("ℹ️ El usuario debe refrescar la orden para ver los cambios\n");
    },
});