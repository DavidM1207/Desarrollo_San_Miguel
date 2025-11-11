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
        
        if (existingPayments && existingPayments.length > 0) {
            const firstPayment = existingPayments[0];
            const existingMethod = firstPayment.payment_method;
            
            if (existingMethod && existingMethod.id !== paymentMethod.id) {
                console.log("⚠️ CAMBIO DE MÉTODO DETECTADO");
                console.log("De:", existingMethod.name, "→", paymentMethod.name);
                
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
                        return;
                    }
                }

                const approval = await this._requestManagerPinAuthorization(existingMethod, paymentMethod);
                
                if (!approval.approved) {
                    console.log("❌ Cambio BLOQUEADO");
                    return;
                }

                console.log("✅ Cambio AUTORIZADO por:", approval.manager_name);
                
                currentOrder.add_payment_method_change(
                    firstPayment.cid,
                    existingMethod,
                    paymentMethod,
                    approval.manager_name
                );
            }
        } 
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
        
        // Usar NumberPopup nativo con isPassword: true
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
            isPassword: true  // ← NUEVA PROPIEDAD
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

        console.log("Validando PIN");
        
        const validation = await this._validateManagerPin(pin);
        
        if (validation.valid) {
            console.log("✅ PIN válido");
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
            
            const employees = await this.orm.searchRead(
                'hr.employee',
                [['pin', '=', String(pin)]],
                ['name', 'user_id']
            );

            console.log("1. Empleados encontrados:", employees.length);

            if (employees.length === 0) {
                return { 
                    valid: false,
                    error_message: "No existe ningún empleado con ese PIN."
                };
            }

            const employee = employees[0];
            console.log("2. Empleado:", employee.name);

            if (!employee.user_id || employee.user_id.length === 0) {
                return { 
                    valid: false,
                    error_message: "El empleado no tiene usuario asociado."
                };
            }

            const userId = employee.user_id[0];
            console.log("3. User ID:", userId);

            console.log("4. Buscando grupo 'POS Payment Manager'...");
            
            const groups = await this.orm.searchRead(
                'res.groups',
                [['name', '=', 'POS Payment Manager']],
                ['id', 'name']
            );

            if (groups.length === 0) {
                console.error("❌ No se encontró el grupo");
                return { 
                    valid: false,
                    error_message: "Error: No se encontró el grupo de gerentes."
                };
            }

            const groupId = groups[0].id;
            console.log("5. Group ID:", groupId);

            console.log("6. Obteniendo grupos del usuario...");
            
            const users = await this.orm.searchRead(
                'res.users',
                [['id', '=', userId]],
                ['id', 'name', 'groups_id']
            );

            if (users.length === 0) {
                console.error("❌ Usuario no encontrado");
                return { 
                    valid: false,
                    error_message: "Error: Usuario no encontrado."
                };
            }

            const user = users[0];
            console.log("7. Usuario encontrado:", user.name);
            console.log("8. Grupos del usuario:", user.groups_id);

            const hasGroup = user.groups_id && user.groups_id.includes(groupId);
            
            console.log("9. ¿Usuario tiene el grupo?:", hasGroup);

            if (hasGroup) {
                console.log("✅ AUTORIZADO");
                console.log("═══════════════════════════════════════");
                return {
                    valid: true,
                    manager_name: employee.name
                };
            } else {
                console.log("❌ DENEGADO");
                console.log("═══════════════════════════════════════");
                return { 
                    valid: false,
                    error_message: "El empleado '" + employee.name + "' no tiene permisos de gerente."
                };
            }

        } catch (error) {
            console.error("❌ ERROR validando PIN");
            console.error("Mensaje:", error.message);
            
            return { 
                valid: false,
                error_message: "Error del sistema: " + error.message
            };
        }
    },
});