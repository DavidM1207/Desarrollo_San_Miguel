/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        
        console.log("🔵 POS Order Sync - Configurando");
        
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
            console.error("❌ ERROR en setup:", error);
        }
    },
    
    _onBusNotification(event) {
        if (!event?.detail) return;
        
        for (const { type, payload } of event.detail) {
            if (type === "pos_payment_approved") {
                console.log("🎯 PAGO APROBADO - Payload:", payload);
                this._handlePaymentApproved(payload);
            }
        }
    },
    
    _handlePaymentApproved(payload) {
        console.log("\n╔═══════════════════════════════════════╗");
        console.log("║  🎯 ACTUALIZANDO MÉTODO DE PAGO       ║");
        console.log("╚═══════════════════════════════════════╝");
        
        const { pos_reference, old_payment_method_id, new_payment_method_id, amount } = payload;
        
        console.log("Buscando orden:", pos_reference);
        console.log("Cambiar de método ID", old_payment_method_id, "→", new_payment_method_id);
        
        // ✅ BUSCAR POR NAME (que sí está disponible)
        const allOrders = this.get_order_list();
        console.log("Total órdenes:", allOrders.length);
        
        let targetOrder = null;
        
        for (const order of allOrders) {
            console.log(`  Comparando: "${order.name}" === "${pos_reference}"`);
            
            // Buscar por name (que contiene la referencia)
            if (order.name === pos_reference) {
                targetOrder = order;
                console.log("  ✅ ENCONTRADA!");
                break;
            }
        }
        
        if (!targetOrder) {
            console.error("❌ ORDEN NO ENCONTRADA");
            return;
        }
        
        console.log("✅ Orden encontrada:", targetOrder.name);
        
        // Cambiar a esta orden si no es la actual
        const currentOrder = this.get_order();
        if (currentOrder?.name !== targetOrder.name) {
            console.log("Cambiando a la orden...");
            this.set_order(targetOrder);
        }
        
        // Buscar método nuevo
        const newMethod = this.payment_methods.find(pm => pm.id === new_payment_method_id);
        
        if (!newMethod) {
            console.error("❌ Método nuevo no encontrado");
            return;
        }
        
        console.log("✅ Método nuevo:", newMethod.name);
        
        // OBTENER PAYMENTLINES ANTES
        const before = targetOrder.get_paymentlines();
        console.log("\n💳 ANTES:", before.length, "líneas");
        before.forEach((pl, i) => {
            console.log(`  [${i}] ${pl.payment_method?.name} - ${pl.amount}`);
        });
        
        // ELIMINAR MÉTODO ANTIGUO
        console.log("\n🗑️ Eliminando método antiguo (ID:", old_payment_method_id + ")");
        let removed = 0;
        
        for (const pl of before) {
            if (pl.payment_method?.id === old_payment_method_id) {
                console.log("  Eliminando:", pl.payment_method.name);
                targetOrder.remove_paymentline(pl);
                removed++;
            }
        }
        
        console.log("✅ Eliminados:", removed);
        
        // VERIFICAR DESPUÉS DE ELIMINAR
        const after = targetOrder.get_paymentlines();
        console.log("\n💳 DESPUÉS DE ELIMINAR:", after.length, "líneas");
        after.forEach((pl, i) => {
            console.log(`  [${i}] ${pl.payment_method?.name} - ${pl.amount}`);
        });
        
        // AGREGAR MÉTODO NUEVO
        console.log("\n➕ Agregando:", newMethod.name, "Monto:", amount);
        
        const newPl = targetOrder.add_paymentline(newMethod);
        
        if (newPl) {
            newPl.set_amount(amount);
            console.log("✅ AGREGADO");
        } else {
            console.error("❌ ERROR al agregar");
            return;
        }
        
        // ESTADO FINAL
        const final = targetOrder.get_paymentlines();
        console.log("\n📊 FINAL:", final.length, "líneas");
        final.forEach((pl, i) => {
            console.log(`  [${i}] ${pl.payment_method?.name} - ${pl.amount}`);
        });
        
        // Notificación
        this.env.services.notification.add(
            `✅ ${targetOrder.name}: ${newMethod.name}`,
            { type: "success", title: "Pago Aprobado" }
        );
        
        console.log("\n✅ COMPLETADO\n");
    },
});