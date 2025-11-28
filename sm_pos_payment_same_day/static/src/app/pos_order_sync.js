/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

console.log("🔵 MÓDULO pos_order_sync.js CARGADO");

patch(PosStore.prototype, {
    async setup() {
        console.log("🔵 PosStore.setup() - INICIO");
        
        await super.setup(...arguments);
        
        console.log("═══════════════════════════════════════");
        console.log("🔵 POS Order Sync - Configurando");
        console.log("═══════════════════════════════════════");
        console.log("Usuario:", this.user?.name);
        console.log("Partner ID (completo):", this.user?.partner_id);
        console.log("Bus Service disponible:", !!this.env.services.bus_service);
        console.log("═══════════════════════════════════════");
        
        try {
            // ✅ NO extraer el ID, usar el array completo [id, nombre]
            const partnerId = this.user?.partner_id;
            
            if (partnerId) {
                console.log("🔵 Agregando canal con:", partnerId);
                this.env.services.bus_service.addChannel(partnerId);
                console.log("✅ Canal agregado exitosamente");
            } else {
                console.error("❌ No hay partner_id");
                return;
            }
            
            // Registrar listener de notificaciones
            console.log("🔵 Registrando listener de notificaciones...");
            this.env.services.bus_service.addEventListener("notification", (event) => {
                console.log("🔔 NOTIFICACIÓN RECIBIDA");
                this._onBusNotification(event);
            });
            console.log("✅ Listener registrado exitosamente");
            
        } catch (error) {
            console.error("❌ ERROR en setup:", error);
            console.error("Stack:", error.stack);
        }
        
        console.log("🔵 PosStore.setup() - FIN");
    },
    
    /**
     * Manejar notificaciones del bus
     */
    _onBusNotification(event) {
        console.log("\n");
        console.log("═══════════════════════════════════════");
        console.log("🔔 _onBusNotification EJECUTADO");
        console.log("═══════════════════════════════════════");
        
        if (!event || !event.detail) {
            console.log("❌ No hay event.detail");
            return;
        }
        
        const notifications = event.detail;
        console.log("📦 Total notificaciones:", notifications.length);
        
        for (let i = 0; i < notifications.length; i++) {
            const notification = notifications[i];
            console.log(`\n--- 📨 Notificación ${i + 1} ---`);
            console.log("Tipo:", notification.type);
            console.log("Payload:", notification.payload);
            
            if (notification.type === "pos_payment_approved") {
                console.log("🎯🎯🎯 ¡PAGO APROBADO!");
                this._handlePaymentApproved(notification.payload);
            }
        }
        
        console.log("═══════════════════════════════════════\n");
    },
    
    /**
     * Manejar la aprobación de un pago
     */
    _handlePaymentApproved(payload) {
        console.log("\n╔═══════════════════════════════════════╗");
        console.log("║  🎯 PROCESANDO PAGO APROBADO          ║");
        console.log("╚═══════════════════════════════════════╝");
        
        const { pos_order_id, old_payment_method_id, new_payment_method_id, amount } = payload;
        
        console.log("\n📋 PAYLOAD:");
        console.log("  pos_order_id:", pos_order_id);
        console.log("  old_payment_method_id:", old_payment_method_id);
        console.log("  new_payment_method_id:", new_payment_method_id);
        console.log("  amount:", amount);
        
        const currentOrder = this.get_order();
        
        if (!currentOrder) {
            console.error("❌ NO HAY ORDEN ACTUAL");
            return;
        }
        
        console.log("\n📦 ORDEN ACTUAL:");
        console.log("  ID:", currentOrder.id);
        console.log("  Nombre:", currentOrder.name);
        
        if (currentOrder.id !== pos_order_id) {
            console.warn("⚠️ NO ES LA ORDEN CORRECTA");
            return;
        }
        
        console.log("✅ ES LA ORDEN CORRECTA");
        
        // Buscar método nuevo
        const newPaymentMethod = this.payment_methods.find(pm => pm.id === new_payment_method_id);
        
        if (!newPaymentMethod) {
            console.error("❌ MÉTODO NUEVO NO ENCONTRADO");
            return;
        }
        
        console.log("✅ Método nuevo:", newPaymentMethod.name);
        
        // Obtener paymentlines actuales
        const paymentlines = currentOrder.get_paymentlines();
        console.log("\n💳 PAYMENTLINES ANTES:", paymentlines.length);
        paymentlines.forEach((pl, i) => {
            console.log(`  [${i}] ${pl.payment_method?.name} - ${pl.amount}`);
        });
        
        // Eliminar pagos del método antiguo
        console.log("\n🗑️ ELIMINANDO MÉTODO ANTIGUO (ID: " + old_payment_method_id + ")");
        let removed = 0;
        
        for (const pl of paymentlines) {
            if (pl.payment_method && pl.payment_method.id === old_payment_method_id) {
                console.log("  Eliminando:", pl.payment_method.name, pl.amount);
                currentOrder.remove_paymentline(pl);
                removed++;
            }
        }
        
        console.log("✅ Eliminados:", removed);
        
        // Agregar nuevo método
        console.log("\n➕ AGREGANDO MÉTODO NUEVO");
        const newPl = currentOrder.add_paymentline(newPaymentMethod);
        
        if (newPl) {
            newPl.set_amount(amount);
            console.log("✅ Agregado:", newPaymentMethod.name, amount);
        } else {
            console.error("❌ ERROR AL AGREGAR");
            return;
        }
        
        // Estado final
        const finalPaymentlines = currentOrder.get_paymentlines();
        console.log("\n📊 PAYMENTLINES FINALES:", finalPaymentlines.length);
        finalPaymentlines.forEach((pl, i) => {
            console.log(`  [${i}] ${pl.payment_method?.name} - ${pl.amount}`);
        });
        
        // Notificación visual
        this.env.services.notification.add(
            "✅ Pago aprobado: " + newPaymentMethod.name,
            {
                type: "success",
                title: "Pago Aprobado",
            }
        );
        
        console.log("\n╔═══════════════════════════════════════╗");
        console.log("║      ✅ COMPLETADO                    ║");
        console.log("╚═══════════════════════════════════════╝\n");
    },
});

console.log("🔵 MÓDULO pos_order_sync.js PATCH APLICADO");