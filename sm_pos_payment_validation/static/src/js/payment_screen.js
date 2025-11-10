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
            console.log("No se pudo obtener el método de pago, continuando con super");
            return super.addNewPaymentLine(...arguments);
        }
        
        console.log("=== VALIDACIÓN MÉTODO DE PAGO ===");
        console.log("Método:", paymentMethod.name);
        
        const currentOrder = this.currentOrder;
        const existingPayments = currentOrder.get_paymentlines();
        
        console.log("Pagos existentes:", existingPayments.length);
        
        if (existingPayments && existingPayments.length > 0) {
            const firstPayment = existingPayments[0];
            const existingMethod = firstPayment.payment_method;
            
            if (existingMethod && existingMethod.id !== paymentMethod.id) {
                console.log("⚠️ CAMBIO DETECTADO:", existingMethod.name, "->", paymentMethod.name);
                
                if (paymentMethod.is_cash_count) {
                    const confirmCash = await this.popup.add(ConfirmPopup, {
                        title: _t("⚠️ ADVERTENCIA: Pago en Efectivo"),
                        body: _t(
                            "Estás cambiando a EFECTIVO.\n\n" +
                            "⚠️ Solo usa efectivo si el cliente REALMENTE pagó en efectivo.\n\n" +
                            "Método actual: " + existingMethod.name + "\n\n" +
                            "¿El pago es realmente en efectivo?"
                        ),
                    });

                    if (!confirmCash) {
                        console.log("❌ Cambio a efectivo cancelado");
                        return;
                    }
                }

                const approval = await this._requestManagerApproval(existingMethod, paymentMethod);
                
                if (!approval.approved) {
                    console.log("❌ Cambio no autorizado");
                    await this.popup.add(ErrorPopup, {
                        title: _t("Cambio No Autorizado"),
                        body: _t(
                            "No puedes cambiar el método de pago sin autorización.\n\n" +
                            "Método actual: " + existingMethod.name + "\n" +
                            "Método solicitado: " + paymentMethod.name
                        ),
                    });
                    return;
                }

                console.log("✓ Cambio autorizado por:", approval.manager_name);
                
                currentOrder.add_payment_method_change(
                    firstPayment.cid,
                    existingMethod,
                    paymentMethod,
                    approval.manager_name
                );
            }
        } else if (paymentMethod.is_cash_count) {
            console.log("Primera selección: efectivo");
            const confirmCash = await this.popup.add(ConfirmPopup, {
                title: _t("💵 Pago en Efectivo"),
                body: _t("Vas a procesar un pago en EFECTIVO.\n\n¿El cliente está pagando en efectivo?"),
            });

            if (!confirmCash) {
                console.log("❌ Efectivo cancelado");
                return;
            }
        }

        console.log("Continuando con super");
        return super.addNewPaymentLine(...arguments);
    },

    async _requestManagerApproval(oldMethod, newMethod) {
        console.log("Solicitando aprobación...");
        
        const isManager = await this._checkManagerPermission();
        console.log("Es gerente:", isManager);

        const userName = this.pos.user?.name || 'Usuario';

        if (isManager) {
            const confirm = await this.popup.add(ConfirmPopup, {
                title: _t("Autorización de Gerente"),
                body: _t(
                    "Como gerente, puedes autorizar:\n\n" +
                    "De: " + oldMethod.name + "\n" +
                    "A: " + newMethod.name + "\n\n" +
                    "¿Autorizar?"
                ),
            });

            return {
                approved: confirm,
                manager_name: userName
            };
        }

        const { confirmed, payload: pin } = await this.popup.add(NumberPopup, {
            title: _t("PIN de Gerente Requerido"),
            body: _t(
                "CAMBIO DE MÉTODO DE PAGO\n\n" +
                "De: " + oldMethod.name + "\n" +
                "A: " + newMethod.name + "\n\n" +
                "Ingresa el PIN de gerente:"
            ),
            startingValue: "",
        });
        
        if (!confirmed || !pin) {
            return { approved: false };
        }

        const validation = await this._validateManagerPin(pin);
        
        if (validation.valid) {
            await this.popup.add(ErrorPopup, {
                title: _t("✓ Autorizado"),
                body: _t("Cambio autorizado por: " + validation.manager_name),
            });

            return {
                approved: true,
                manager_name: validation.manager_name
            };
        } else {
            await this.popup.add(ErrorPopup, {
                title: _t("PIN Inválido"),
                body: _t("El PIN no es válido o no tiene permisos."),
            });

            return { approved: false };
        }
    },

    async _checkManagerPermission() {
    try {
        console.log("═══════════════════════════════════════");
        console.log("VERIFICANDO PERMISOS - INICIO");
        console.log("═══════════════════════════════════════");
        
        // Obtener el usuario de diferentes formas posibles
        console.log("1. this.pos.user:", this.pos.user);
        console.log("2. this.pos.get_cashier():", this.pos.get_cashier());
        
        let userId = null;
        
        // Método 1: Desde this.pos.user
        if (this.pos.user && this.pos.user.id) {
            userId = this.pos.user.id;
            console.log("✓ User ID obtenido desde this.pos.user.id:", userId);
        }
        
        // Método 2: Desde get_cashier
        if (!userId) {
            const cashier = this.pos.get_cashier();
            if (cashier && cashier.user_id) {
                userId = Array.isArray(cashier.user_id) ? cashier.user_id[0] : cashier.user_id;
                console.log("✓ User ID obtenido desde get_cashier():", userId);
            }
        }
        
        if (!userId) {
            console.error("❌ No se pudo obtener el user ID");
            return false;
        }
        
        console.log("═══════════════════════════════════════");
        console.log("LLAMANDO A has_group");
        console.log("User ID:", userId);
        console.log("Group:", 'sm_pos_payment_validation.group_pos_payment_manager');
        console.log("═══════════════════════════════════════");
        
        // Llamar a has_group
        const result = await this.orm.call(
            'res.users',
            'has_group',
            [userId, 'sm_pos_payment_validation.group_pos_payment_manager']
        );
        
        console.log("═══════════════════════════════════════");
        console.log("RESULTADO has_group:", result);
        console.log(result ? "✅ SÍ TIENE PERMISO" : "❌ NO TIENE PERMISO");
        console.log("═══════════════════════════════════════");
        
        return result;
        
    } catch (error) {
        console.error("═══════════════════════════════════════");
        console.error("❌ ERROR en _checkManagerPermission");
        console.error("Error:", error);
        console.error("Mensaje:", error.message);
        console.error("Stack:", error.stack);
        console.error("═══════════════════════════════════════");
        return false;
    }
},

    async _validateManagerPin(pin) {
        try {
            const employees = await this.orm.searchRead(
                'hr.employee',
                [['pin', '=', String(pin)]],
                ['name', 'user_id']
            );

            if (employees.length > 0) {
                const employee = employees[0];
                
                if (employee.user_id && employee.user_id.length > 0) {
                    const userId = employee.user_id[0];
                    
                    const hasPermission = await this.orm.call(
                        'res.users',
                        'has_group',
                        [userId, 'sm_pos_payment_validation.group_pos_payment_manager']
                    );

                    if (hasPermission) {
                        return {
                            valid: true,
                            manager_name: employee.name
                        };
                    }
                }
            }

            return { valid: false };
        } catch (error) {
            console.error("Error validando PIN:", error);
            return { valid: false };
        }
    },
});