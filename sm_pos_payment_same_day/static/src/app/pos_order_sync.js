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
        console.log("Partner ID (raw):", this.user?.partner_id);
        
        // ✅ CORRECCIÓN: Extraer el ID numérico del array
        let partnerId = this.user?.partner_id;
        if (Array.isArray(partnerId)) {
            partnerId = partnerId[0];
        }
        console.log("Partner ID (extraído):", partnerId);
        console.log("Partner ID (tipo):", typeof partnerId);
        
        console.log("Bus Service disponible:", !!this.env.services.bus_service);
        console.log("═══════════════════════════════════════");
        
        try {
            // Agregar canal del partner al bus con el ID correcto
            if (partnerId) {
                console.log("🔵 Agregando canal con ID:", partnerId);
                this.env.services.bus_service.addChannel(partnerId);
                console.log("✅ Canal agregado exitosamente");
            } else {
                console.error("❌ No hay partner_id válido");
                return;
            }
            
            // Registrar listener de notificaciones
            console.log("🔵 Registrando listener de notificaciones...");
            this.env.services.bus_service.addEventListener("notification", (event) => {
                console.log("🔔 NOTIFICACIÓN RECIBIDA (cualquier tipo)");
                console.log("Event completo:", event);
                this._onBusNotification(event);
            });
            console.log("✅ Listener registrado exitosamente");
            
            // Guardar el partner_id para futuras referencias
            this._approvalPartnerId = partnerId;
            
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
            console.log("Event recibido:", event);
            return;
        }
        
        const notifications = event.detail;
        console.log("📦 Total notificaciones recibidas:", notifications.length);
        
        for (let i = 0; i < notifications.length; i++) {
            const notification = notifications[i];
            console.log(`\n--- 📨 Notificación ${i + 1} de ${notifications.length} ---`);
            console.log("Objeto completo:", notification);
            console.log("Tipo:", notification.type);
            console.log("Payload:", notification.payload);
            
            if (notification.type === "pos_payment_approved") {
                console.log("🎯🎯🎯 ¡ES UNA NOTIFICACIÓN DE PAGO APROBADO!");
                this._handlePaymentApproved(notification.payload);
            } else {
                console.log("⚪ Tipo diferente (" + notification.type + "), ignorando");
            }
        }
        
        console.log("═══════════════════════════════════════\n");
    },
    
    /**
     * Manejar la aprobación de un pago
     */
    _handlePaymentApproved(payload) {
        console.log("\n");
        console.log("╔═══════════════════════════════════════╗");
        console.log("║  🎯 _handlePaymentApproved EJECUTADO  ║");
        console.log("╚═══════════════════════════════════════╝");
        
        if (!payload) {
            console.error("❌ No hay payload");
            return;
        }
        
        const { pos_order_id, old_payment_method_id, new_payment_method_id, amount } = payload;
        
        console.log("\n📋 DATOS DEL PAYLOAD:");
        console.log("  pos_order_id:", pos_order_id, "(tipo:", typeof pos_order_id + ")");
        console.log("  old_payment_method_id:", old_payment_method_id, "(tipo:", typeof old_payment_method_id + ")");
        console.log("  new_payment_method_id:", new_payment_method_id, "(tipo:", typeof new_payment_method_id + ")");
        console.log("  amount:", amount, "(tipo:", typeof amount + ")");
        
        // Obtener la orden actual
        const currentOrder = this.get_order();
        
        if (!currentOrder) {
            console.error("❌ NO HAY ORDEN ACTUAL EN EL POS");
            return;
        }
        
        console.log("\n📦 ORDEN ACTUAL EN EL POS:");
        console.log("  ID:", currentOrder.id, "(tipo:", typeof currentOrder.id + ")");
        console.log("  Nombre:", currentOrder.name);
        console.log("  Referencia:", currentOrder.pos_reference);
        
        // Verificar si es la orden correcta
        if (currentOrder.id !== pos_order_id) {
            console.warn("⚠️⚠️⚠️ NO ES LA ORDEN ACTUAL");
            console.log("   Orden en POS:", currentOrder.id, "(tipo:", typeof currentOrder.id + ")");
            console.log("   Orden notificada:", pos_order_id, "(tipo:", typeof pos_order_id + ")");
            console.log("   ¿Son iguales?", currentOrder.id === pos_order_id);
            console.log("   ¿Son iguales (==)?", currentOrder.id == pos_order_id);
            return;
        }
        
        console.log("✅✅✅ ES LA ORDEN ACTUAL - Procediendo a actualizar...");
        
        // Buscar el nuevo método de pago
        console.log("\n🔍 Buscando método de pago nuevo...");
        console.log("ID a buscar:", new_payment_method_id);
        console.log("Total métodos disponibles:", this.payment_methods.length);
        
        const newPaymentMethod = this.payment_methods.find(pm => pm.id === new_payment_method_id);
        
        if (!newPaymentMethod) {
            console.error("❌❌❌ MÉTODO DE PAGO NUEVO NO ENCONTRADO");
            console.log("Buscando ID:", new_payment_method_id);
            console.log("\n📋 Métodos disponibles:");
            this.payment_methods.forEach(pm => {
                console.log("  - ID:", pm.id, "Nombre:", pm.name, "¿Coincide?", pm.id === new_payment_method_id);
            });
            return;
        }
        
        console.log("✅ Método nuevo encontrado:", newPaymentMethod.name, "(ID:", newPaymentMethod.id + ")");
        
        // Obtener líneas de pago actuales ANTES de modificar
        const paymentlinesBefore = currentOrder.get_paymentlines();
        console.log("\n💳 PAYMENTLINES ANTES DE MODIFICAR:", paymentlinesBefore.length);
        
        paymentlinesBefore.forEach((pl, index) => {
            console.log(`  [${index}] ${pl.payment_method?.name || 'N/A'} (ID: ${pl.payment_method?.id || 'N/A'}) - Monto: ${pl.amount}`);
        });
        
        // Buscar y eliminar líneas con el método antiguo
        console.log("\n🗑️ ELIMINANDO PAGOS ANTIGUOS...");
        console.log("Método a eliminar (ID):", old_payment_method_id);
        
        let removedCount = 0;
        const linesToRemove = paymentlinesBefore.filter(pl => 
            pl.payment_method && pl.payment_method.id === old_payment_method_id
        );
        
        console.log("Líneas encontradas para eliminar:", linesToRemove.length);
        
        for (const pl of linesToRemove) {
            console.log("  🗑️ Eliminando:", pl.payment_method.name, "Monto:", pl.amount);
            try {
                currentOrder.remove_paymentline(pl);
                removedCount++;
                console.log("  ✅ Eliminada exitosamente");
            } catch (error) {
                console.error("  ❌ Error al eliminar:", error);
            }
        }
        
        console.log("📊 Total eliminadas:", removedCount);
        
        // Verificar paymentlines DESPUÉS de eliminar
        const paymentlinesAfterRemove = currentOrder.get_paymentlines();
        console.log("\n💳 PAYMENTLINES DESPUÉS DE ELIMINAR:", paymentlinesAfterRemove.length);
        paymentlinesAfterRemove.forEach((pl, index) => {
            console.log(`  [${index}] ${pl.payment_method?.name || 'N/A'} - Monto: ${pl.amount}`);
        });
        
        // Agregar nuevo paymentline
        console.log("\n➕ AGREGANDO NUEVO PAYMENTLINE...");
        console.log("  Método:", newPaymentMethod.name);
        console.log("  Monto a establecer:", amount);
        
        try {
            const newPaymentline = currentOrder.add_paymentline(newPaymentMethod);
            
            if (newPaymentline) {
                console.log("  ✅ Paymentline creada");
                console.log("  CID:", newPaymentline.cid);
                console.log("  Monto inicial:", newPaymentline.amount);
                
                newPaymentline.set_amount(amount);
                console.log("  Monto después de set_amount:", newPaymentline.amount);
                console.log("  ✅✅✅ PAYMENTLINE AGREGADA EXITOSAMENTE");
            } else {
                console.error("  ❌❌❌ add_paymentline retornó null/undefined");
            }
        } catch (error) {
            console.error("❌ Error al agregar paymentline:", error);
            console.error("Stack:", error.stack);
        }
        
        // Verificar estado FINAL
        const paymentlinesFinal = currentOrder.get_paymentlines();
        console.log("\n📊 ESTADO FINAL DE PAYMENTLINES:", paymentlinesFinal.length);
        paymentlinesFinal.forEach((pl, index) => {
            console.log(`  [${index}] ${pl.payment_method?.name || 'N/A'} (ID: ${pl.payment_method?.id}) - Monto: ${pl.amount}`);
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
        
        console.log("\n╔═══════════════════════════════════════╗");
        console.log("║      ✅ PROCESO COMPLETADO            ║");
        console.log("╚═══════════════════════════════════════╝\n");
    },
});

console.log("🔵 MÓDULO pos_order_sync.js PATCH APLICADO");