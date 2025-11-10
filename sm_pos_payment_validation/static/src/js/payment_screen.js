/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { AlertPopup } from "@point_of_sale/app/utils/input_popups/alert_popup";
import { ConfirmPopup } from "@point_of_sale/app/utils/input_popups/confirm_popup";

patch(PaymentScreen.prototype, {
    
    async addNewPaymentLine({ detail: paymentMethod }) {
        const currentOrder = this.currentOrder;
        
        // Verificar si hay pagos existentes con métodos diferentes
        const existingPayments = currentOrder.get_paymentlines();
        
        if (existingPayments.length > 0) {
            const existingMethod = existingPayments[0].payment_method;
            
            // Si se está cambiando el método de pago
            if (existingMethod && existingMethod.id !== paymentMethod.id) {
                
                // Verificar si es cambio a efectivo - mostrar advertencia
                if (paymentMethod.is_cash_count) {
                    const confirmCash = await this.popup.add(ConfirmPopup, {
                        title: _t("⚠️ Advertencia: Pago en Efectivo"),
                        body: _t(
                            "Estás seleccionando EFECTIVO como método de pago.\n\n" +
                            "⚠️ IMPORTANTE: Solo selecciona efectivo si realmente el cliente pagó en efectivo.\n\n" +
                            "Si fue transferencia, tarjeta u otro método, selecciona el método correcto.\n\n" +
                            "¿Confirmas que el pago es en EFECTIVO?"
                        ),
                        confirmText: _t("Sí, es Efectivo"),
                        cancelText: _t("No, cancelar"),
                    });

                    if (!confirmCash) {
                        return; // Cancelar si no confirma
                    }
                }

                // Requerir aprobación de gerente para el cambio
                const managerApproval = await this._requestManagerApproval(
                    existingMethod, 
                    paymentMethod
                );

                if (!managerApproval.approved) {
                    await this.popup.add(AlertPopup, {
                        title: _t("Cambio de Método de Pago Denegado"),
                        body: _t(
                            "No puedes cambiar el método de pago sin la aprobación del gerente.\n\n" +
                            "Método actual: " + existingMethod.name + "\n" +
                            "Método solicitado: " + paymentMethod.name
                        ),
                    });
                    return; // No permitir el cambio
                }

                // Registrar el cambio aprobado
                currentOrder.add_payment_method_change(
                    existingMethod,
                    paymentMethod,
                    managerApproval.manager_name
                );
            }
            // Si es el mismo método pero es efectivo, solo advertir
            else if (existingMethod && existingMethod.id === paymentMethod.id && paymentMethod.is_cash_count) {
                // Mostrar advertencia de efectivo sin bloquear
                this.popup.add(AlertPopup, {
                    title: _t("Recordatorio: Pago en Efectivo"),
                    body: _t(
                        "Recuerda que estás procesando un pago en EFECTIVO.\n\n" +
                        "Verifica que el cliente realmente pagó en efectivo."
                    ),
                });
            }
        }
        // Primera vez que se selecciona método de pago en efectivo
        else if (paymentMethod.is_cash_count && existingPayments.length === 0) {
            const confirmCash = await this.popup.add(ConfirmPopup, {
                title: _t("⚠️ Confirmación: Pago en Efectivo"),
                body: _t(
                    "Estás seleccionando EFECTIVO como método de pago.\n\n" +
                    "¿El cliente está pagando en efectivo?"
                ),
                confirmText: _t("Sí, es Efectivo"),
                cancelText: _t("No, elegir otro método"),
            });

            if (!confirmCash) {
                return;
            }
        }

        // Proceder con el pago normal
        return super.addNewPaymentLine(...arguments);
    },

    async _requestManagerApproval(oldMethod, newMethod) {
        // Verificar si el usuario actual tiene permisos de manager
        const currentUser = this.pos.get_cashier();
        const hasManagerPermission = await this._checkManagerPermission(currentUser);

        if (hasManagerPermission) {
            // Si ya es manager, solo confirmar
            const confirm = await this.popup.add(ConfirmPopup, {
                title: _t("Aprobación de Gerente"),
                body: _t(
                    "Cambio de método de pago:\n\n" +
                    "De: " + oldMethod.name + "\n" +
                    "A: " + newMethod.name + "\n\n" +
                    "¿Aprobar este cambio?"
                ),
                confirmText: _t("Aprobar"),
                cancelText: _t("Cancelar"),
            });

            return {
                approved: confirm,
                manager_name: currentUser.name
            };
        }

        // Solicitar PIN de gerente
        const { confirmed, payload: pin } = await this.popup.add(NumberPopup, {
            title: _t("Aprobación de Gerente Requerida"),
            body: _t(
                "Se requiere aprobación del gerente para cambiar el método de pago.\n\n" +
                "De: " + oldMethod.name + "\n" +
                "A: " + newMethod.name + "\n\n" +
                "Por favor, ingresa el PIN del gerente:"
            ),
            startingValue: "",
        });

        if (!confirmed) {
            return { approved: false };
        }

        // Validar el PIN del gerente
        const managerValidation = await this._validateManagerPin(pin);
        
        if (managerValidation.valid) {
            await this.popup.add(AlertPopup, {
                title: _t("✓ Aprobación Exitosa"),
                body: _t(
                    "Cambio de método de pago aprobado por: " + managerValidation.manager_name
                ),
            });

            return {
                approved: true,
                manager_name: managerValidation.manager_name
            };
        } else {
            await this.popup.add(AlertPopup, {
                title: _t("✗ PIN Incorrecto"),
                body: _t("El PIN ingresado no corresponde a un gerente autorizado."),
            });

            return { approved: false };
        }
    },

    async _checkManagerPermission(user) {
        // Verificar si el usuario tiene el grupo de manager
        try {
            const result = await this.orm.call(
                'res.users',
                'has_group',
                [user.id || this.pos.user.id, 'pos_payment_validation.group_pos_payment_manager']
            );
            return result;
        } catch (error) {
            console.error("Error checking manager permission:", error);
            return false;
        }
    },

    async _validateManagerPin(pin) {
        // Buscar empleado con ese PIN y verificar permisos
        try {
            const employees = await this.orm.call(
                'hr.employee',
                'search_read',
                [[['pin', '=', pin]]],
                ['name', 'user_id']
            );

            if (employees.length > 0) {
                const employee = employees[0];
                const hasPermission = await this.orm.call(
                    'res.users',
                    'has_group',
                    [employee.user_id[0], 'pos_payment_validation.group_pos_payment_manager']
                );

                if (hasPermission) {
                    return {
                        valid: true,
                        manager_name: employee.name
                    };
                }
            }

            return { valid: false };
        } catch (error) {
            console.error("Error validating manager PIN:", error);
            return { valid: false };
        }
    },

    async validateOrder(isForceValidate) {
        const currentOrder = this.currentOrder;
        const changes = currentOrder.get_payment_method_changes();

        // Log de cambios para auditoría
        if (changes.length > 0) {
            console.log("Payment method changes:", changes);
        }

        return super.validateOrder(...arguments);
    },
});