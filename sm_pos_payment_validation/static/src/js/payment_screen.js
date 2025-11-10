/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";

patch(PaymentScreen.prototype, {
    
    async addNewPaymentLine(event) {
        const paymentMethod = event?.detail || event;
        
        if (!paymentMethod || !paymentMethod.name) {
            return super.addNewPaymentLine(...arguments);
        }
        
        console.log("=== VALIDACIÓN MÉTODO DE PAGO ===");
        console.log("Método:", paymentMethod.name);
        
        const currentOrder = this.currentOrder;
        const existingPayments = currentOrder.get_paymentlines();
        
        // Si ya hay líneas de pago y se intenta cambiar el método
        if (existingPayments && existingPayments.length > 0) {
            const firstPayment = existingPayments[0];
            const existingMethod = firstPayment.payment_method;
            
            if (existingMethod && existingMethod.id !== paymentMethod.id) {
                console.log("⚠️ CAMBIO DE MÉTODO DETECTADO");
                console.log("De:", existingMethod.name, "→", paymentMethod.name);
                
                // Advertencia especial si es cambio a efectivo
                if (paymentMethod.is_cash_count) {
                    const confirmCash = await this.popup.add(ConfirmPopup, {
                        title: _t("⚠️ ADVERTENCIA: Cambio a Efectivo"),
                        body: _t(
                            "Estás intentando cambiar a EFECTIVO.\n\n" +
                            "⚠️ IMPORTANTE:\n" +
                            "• Solo usa efectivo si el cliente REALMENTE pagó en efectivo\n" +
                            "• NO uses efectivo para transferencias o pagos con tarjeta\n\n" +
                            "Método actual: " + existingMethod.name + "\n\n" +
                            "¿El cliente pagó REALMENTE en EFECTIVO?"
                        ),
                    });

                    if (!confirmCash) {
                        console.log("❌ Cambio a efectivo cancelado");
                        return; // BLOQUEAR
                    }
                }

                // SIEMPRE solicitar PIN de gerente (sin importar quién es el cajero)
                const approval = await this._requestManagerPinAuthorization(existingMethod, paymentMethod);
                
                if (!approval.approved) {
                    console.log("❌ Cambio BLOQUEADO");
                    return; // BLOQUEAR
                }

                console.log("✅ Cambio AUTORIZADO por:", approval.manager_name);
                
                // Registrar el cambio
                currentOrder.add_payment_method_change(
                    firstPayment.cid,
                    existingMethod,
                    paymentMethod,
                    approval.manager_name
                );
            }
        } 
        // Primera selección de efectivo
        else if (paymentMethod.is_cash_count) {
            const confirmCash = await this.popup.add(ConfirmPopup, {
                title: _t("💵 Pago en Efectivo"),
                body: _t("Vas a procesar un pago en EFECTIVO.\n\n¿El cliente está pagando en efectivo?"),
            });

            if (!confirmCash) {
                console.log("❌ Efectivo cancelado");
                return;
            }
        }

        console.log("✅ Permitiendo agregar línea de pago");
        return super.addNewPaymentLine(...arguments);
    },

    async _requestManagerPinAuthorization(oldMethod, newMethod) {
        console.log("═══════════════════════════════════════");
        console.log("SOLICITANDO AUTORIZACIÓN DE GERENTE");
        console.log("═══════════════════════════════════════");
        
        // SIEMPRE pedir PIN (sin verificar si el usuario actual es gerente)
        const { confirmed, payload: pin } = await this.popup.add(NumberPopup, {
            title: _t("🔐 Autorización de Gerente Requerida"),
            body: _t(
                "CAMBIO DE MÉTODO DE PAGO\n\n" +
                "De: " + oldMethod.name + "\n" +
                "A: " + newMethod.name + "\n\n" +
                "═════════════════════════════\n" +
                "Se requiere autorización de gerente.\n\n" +
                "Gerente/Encargado: Ingresa tu PIN:"
            ),
            startingValue: "",
        });

        if (!confirmed || !pin) {
            console.log("❌ No se ingresó PIN");
            await this.popup.add(ErrorPopup, {
                title: _t("❌ Cambio Cancelado"),
                body: _t(
                    "El cambio de método de pago ha sido cancelado.\n\n" +
                    "Se requiere autorización de gerente para continuar."
                ),
            });
            return { approved: false };
        }

        console.log("Validando PIN:", pin);
        
        // Validar que el PIN pertenezca a un usuario con permisos
        const validation = await this._validateManagerPin(pin);
        
        if (validation.valid) {
            console.log("✅ PIN válido - Gerente:", validation.manager_name);
            await this.popup.add(ErrorPopup, {
                title: _t("✅ Cambio Autorizado"),
                body: _t("Cambio autorizado por: " + validation.manager_name),
            });
            
            return {
                approved: true,
                manager_name: validation.manager_name
            };
        } else {
            console.log("❌ PIN inválido");
            await this.popup.add(ErrorPopup, {
                title: _t("❌ PIN Inválido"),
                body: _t(
                    "El PIN ingresado no es válido o no tiene permisos de gerente.\n\n" +
                    validation.error_message + "\n\n" +
                    "El cambio ha sido BLOQUEADO."
                ),
            });
            return { approved: false };
        }
    },

    async _validateManagerPin(pin) {
        try {
            console.log("═══════════════════════════════════════");
            console.log("VALIDANDO PIN DE GERENTE");
            console.log("PIN:", pin);
            console.log("═══════════════════════════════════════");
            
            // Buscar empleado por PIN
            const employees = await this.orm.searchRead(
                'hr.employee',
                [['pin', '=', String(pin)]],
                ['name', 'user_id']
            );

            console.log("Empleados encontrados:", employees.length);

            if (employees.length === 0) {
                console.log("❌ No se encontró empleado con ese PIN");
                return { 
                    valid: false,
                    error_message: "No existe ningún empleado con ese PIN."
                };
            }

            const employee = employees[0];
            console.log("Empleado encontrado:", employee.name);

            if (!employee.user_id || employee.user_id.length === 0) {
                console.log("❌ Empleado sin usuario asociado");
                return { 
                    valid: false,
                    error_message: "El empleado '" + employee.name + "' no tiene usuario en el sistema."
                };
            }

            const userId = employee.user_id[0];
            console.log("User ID:", userId);

            // Verificar que el usuario tenga el grupo de gerente
            console.log("Verificando grupo 'sm_pos_payment_validation.group_pos_payment_manager'");
            
            const hasPermission = await this.orm.call(
                'res.users',
                'has_group',
                [userId, 'sm_pos_payment_validation.group_pos_payment_manager']
            );

            console.log("¿Tiene permisos?:", hasPermission);

            if (hasPermission) {
                console.log("✅ AUTORIZADO - PIN válido y tiene permisos");
                return {
                    valid: true,
                    manager_name: employee.name
                };
            } else {
                console.log("❌ DENEGADO - Empleado sin permisos de gerente");
                return { 
                    valid: false,
                    error_message: "El empleado '" + employee.name + "' no tiene permisos de gerente."
                };
            }

        } catch (error) {
            console.error("❌ ERROR validando PIN:", error);
            console.error("Detalles:", error.message);
            return { 
                valid: false,
                error_message: "Error del sistema: " + error.message
            };
        }
    },
});