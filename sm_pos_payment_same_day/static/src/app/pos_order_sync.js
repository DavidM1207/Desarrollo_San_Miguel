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
        console.log("Partner ID:", this.user?.partner_id);
        console.log("Bus Service disponible:", !!this.env.services.bus_service);
        console.log("═══════════════════════════════════════");
        
        try {
            // Agregar canal del partner al bus
            if (this.user?.partner_id) {
                console.log("🔵 Agregando canal:", this.user.partner_id);
                this.env.services.bus_service.addChannel(this.user.partner_id);
                console.log("✅ Canal agregado");
            } else {
                console.error("❌ No hay partner_id");
            }
            
            // Registrar listener de notificaciones
            console.log("🔵 Registrando listener de notificaciones...");
            this.env.services.bus_service.addEventListener("notification", (event) => {
                console.log("🔔 NOTIFICACIÓN RECIBIDA (cualquier tipo)");
                console.log("Event:", event);
                console.log("Detail:", event.detail);
                this._onBusNotification(event);
            });
            console.log("✅ Listener registrado");
            
        } catch (error) {
            console.error("❌ ERROR en setup:", error);
        }
        
        console.log("🔵 PosStore.setup() - FIN");
    },
    
    /**
     * Manejar notificaciones del bus
     */
    _onBusNotification(event) {
        console.log("═══════════════════════════════════════");
        console.log("🔔 _onBusNotification EJECUTADO");
        
        if (!event || !event.detail) {
            console.log("❌ No hay event.detail");
            return;
        }
        
        const notifications = event.detail;
        console.log("Total notificaciones:", notifications.length);
        
        for (let i = 0; i < notifications.length; i++) {
            const notification = notifications[i];
            console.log(`\n--- Notificación ${i + 1} ---`);
            console.log("Tipo:", notification.type);
            console.log("Payload completo:", notification.payload);
            
            if (notification.type === "pos_payment_approved") {
                console.log("🎯 ES UNA NOTIFICACIÓN DE PAGO APROBADO");
                this._handlePaymentApproved(notification.payload);
            } else {
                console.log("⚪ Tipo diferente, ignorando");
            }
        }
        
        console.log("═══════════════════════════════════════");
    },
    
    /**
     * Manejar la aprobación de un pago
     */
    _handlePaymentApproved(payload) {
        console.log("\n");
        console.log("═══════════════════════════════════════");
        console.log("🎯 _handlePaymentApproved EJECUTADO");
        console.log("═══════════════════════════════════════");
        
        if (!payload) {
            console.error("❌ No hay payload");
            return;
        }
        
        const { pos_order_id, old_payment_method_id, new_payment_method_id, amount } = payload;
        
        console.log("📋 DATOS RECIBIDOS:");
        console.log("  pos_order_id:", pos_order_id);
        console.log("  old_payment_method_id:", old_payment_method_id);
        console.log("  new_payment_method_id:", new_payment_method_id);
        console.log("  amount:", amount);
        
        // Obtener la orden actual
        const currentOrder = this.get_order();
        
        if (!currentOrder) {
            console.error("❌ NO HAY ORDEN ACTUAL");
            return;
        }
        
        console.log("\n📦 ORDEN ACTUAL:");
        console.log("  ID:", currentOrder.id);
        console.log("  Nombre:", currentOrder.name);
        console.log("  Referencia:", currentOrder.pos_reference);
        
        // Verificar si es la orden correcta
        if (currentOrder.id !== pos_order_id) {
            console.warn("⚠️ NO ES LA ORDEN ACTUAL");
            console.log("   Orden actual ID:", currentOrder.id);
            console.log("   Orden notificada ID:", pos_order_id);
            return;
        }
        
        console.log("✅ ES LA ORDEN ACTUAL - Procediendo...");
        
        // Buscar el nuevo método de pago
        console.log("\n🔍 Buscando método de pago nuevo (ID: " + new_payment_method_id + ")");
        console.log("Métodos disponibles:", this.payment_methods.length);
        
        const newPaymentMethod = this.payment_methods.find(pm => pm.id === new_payment_method_id);
        
        if (!newPaymentMethod) {
            console.error("❌ MÉTODO DE PAGO NUEVO NO ENCONTRADO");
            console.log("Métodos disponibles:");
            this.payment_methods.forEach(pm => {
                console.log("  - ID:", pm.id, "Nombre:", pm.name);
            });
            return;
        }
        
        console.log("✅ Método nuevo encontrado:", newPaymentMethod.name);
        
        // Obtener líneas de pago actuales
        const paymentlines = currentOrder.get_paymentlines();
        console.log("\n💳 PAYMENTLINES ACTUALES:", paymentlines.length);
        
        paymentlines.forEach((pl, index) => {
            console.log(`  [${index}] Método: ${pl.payment_method?.name || 'N/A'} (ID: ${pl.payment_method?.id || 'N/A'}), Monto: ${pl.amount}`);
        });
        
        // Buscar y eliminar líneas con el método antiguo
        console.log("\n🗑️ ELIMINANDO PAGOS ANTIGUOS (método ID: " + old_payment_method_id + ")");
        let removedCount = 0;
        
        const linesToRemove = paymentlines.filter(pl => 
            pl.payment_method && pl.payment_method.id === old_payment_method_id
        );
        
        console.log("Líneas a eliminar:", linesToRemove.length);
        
        for (const pl of linesToRemove) {
            console.log("  Eliminando:", pl.payment_method.name, pl.amount);
            try {
                currentOrder.remove_paymentline(pl);
                removedCount++;
                console.log("  ✅ Eliminada");
            } catch (error) {
                console.error("  ❌ Error al eliminar:", error);
            }
        }
        
        console.log("✅ Total eliminadas:", removedCount);
        
        // Agregar nuevo paymentline
        console.log("\n➕ AGREGANDO NUEVO PAYMENTLINE");
        console.log("  Método:", newPaymentMethod.name);
        console.log("  Monto:", amount);
        
        try {
            const newPaymentline = currentOrder.add_paymentline(newPaymentMethod);
            
            if (newPaymentline) {
                newPaymentline.set_amount(amount);
                console.log("✅ Paymentline agregada exitosamente");
                console.log("  CID:", newPaymentline.cid);
                console.log("  Monto final:", newPaymentline.amount);
            } else {
                console.error("❌ add_paymentline retornó null/undefined");
            }
        } catch (error) {
            console.error("❌ Error al agregar paymentline:", error);
        }
        
        // Verificar estado final
        const finalPaymentlines = currentOrder.get_paymentlines();
        console.log("\n📊 ESTADO FINAL:");
        console.log("Total paymentlines:", finalPaymentlines.length);
        finalPaymentlines.forEach((pl, index) => {
            console.log(`  [${index}] Método: ${pl.payment_method?.name || 'N/A'}, Monto: ${pl.amount}`);
        });
        
        // Mostrar notificación de éxito
        try {
            this.env.services.notification.add(
                "✅ Pago aprobado. Método actualizado a: " + newPaymentMethod.name,
                {
                    type: "success",
                    title: "Pago Aprobado",
                }
            );
            console.log("✅ Notificación mostrada al usuario");
        } catch (error) {
            console.error("❌ Error al mostrar notificación:", error);
        }
        
        console.log("\n═══════════════════════════════════════");
        console.log("✅ PROCESO COMPLETADO");
        console.log("═══════════════════════════════════════\n");
    },
});

console.log("🔵 MÓDULO pos_order_sync.js PATCH APLICADO");