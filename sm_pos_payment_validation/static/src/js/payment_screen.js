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
        
        console.log("═══════════════════════════════════════");
        console.log("INTENTANDO AGREGAR MÉTODO DE PAGO");
        console.log("Método seleccionado:", paymentMethod.name);
        console.log("═══════════════════════════════════════");
        
        const currentOrder = this.currentOrder;
        const existingPayments = currentOrder.get_paymentlines();
        
        // Si ya hay líneas de pago, estamos intentando cambiar el método
        if (existingPayments && existingPayments.length > 0) {
            const firstPayment = existingPayments[0];
            const existingMethod = firstPayment.payment_method;
            
            if (existingMethod && existingMethod.id !== paymentMethod.id) {
                console.log("CAMBIO DE MÉTODO DETECTADO");
                console.log("Método actual:", existingMethod.name);
                console.log("Método nuevo:", paymentMethod.name);
                
                // VERIFICAR SI EL MÉTODO ACTUAL ES TRANSFERENCIA CON REFERENCIA
                if (this._isTransferWithReference(firstPayment)) {
                    console.log("❌ El método actual es transferencia con referencia");
                    
                    await this.popup.add(ErrorPopup, {
                        title: _t("Método de Pago Protegido"),
                        body: _t(
                            "No puedes cambiar un método de pago por TRANSFERENCIA que ya tiene una referencia/solicitud registrada.\n\n" +
                            "Método actual: " + existingMethod.name + "\n" +
                            "Referencia: " + (firstPayment.payment_reference || firstPayment.transaction_id || "N/A") + "\n\n" +
                            "Si necesitas modificarlo, debes eliminar la línea de pago y crear una nueva."
                        ),
                    });
                    
                    return; // BLOQUEAR el cambio
                }
                
                // Advertencia si el nuevo método es efectivo
                if (paymentMethod.is_cash_count) {
                    const confirmCash = await this.popup.add(ConfirmPopup, {
                        title: _t("ADVERTENCIA: Cambio a Efectivo"),
                        body: _t(
                            "Estás cambiando a EFECTIVO.\n\n" +
                            "IMPORTANTE:\n" +
                            "• Solo usa efectivo si el cliente REALMENTE pagó en efectivo\n" +
                            "• NO uses efectivo para transferencias o pagos con tarjeta\n\n" +
                            "Método actual: " + existingMethod.name + "\n" +
                            "Monto: " + this.env.utils.formatCurrency(firstPayment.amount) + "\n\n" +
                            "¿El cliente pagó REALMENTE en EFECTIVO?"
                        ),
                    });

                    if (!confirmCash) {
                        console.log("❌ Cambio a efectivo cancelado");
                        return;
                    }
                }

                // Solicitar autorización del gerente
                const approval = await this._requestManagerPinAuthorization(existingMethod, paymentMethod);
                
                if (!approval.approved) {
                    console.log("❌ Cambio BLOQUEADO - Sin autorización");
                    return;
                }

                console.log("✅ Cambio AUTORIZADO por:", approval.manager_name);
                
                // REEMPLAZAR EL MÉTODO DE PAGO
                await this._replacePaymentMethod(firstPayment, paymentMethod, approval.manager_name);
                
                return; // No continuar con super porque ya reemplazamos
            }
        } 
        // Primera selección de efectivo
        else if (paymentMethod.is_cash_count) {
            const confirmCash = await this.popup.add(ConfirmPopup, {
                title: _t("Pago en Efectivo"),
                body: _t("Vas a procesar un pago en EFECTIVO.\n\n¿El cliente está pagando en efectivo?"),
            });

            if (!confirmCash) {
                console.log("❌ Efectivo cancelado");
                return;
            }
        }

        console.log("✅ Agregando método de pago normalmente");
        return super.addNewPaymentLine(...arguments);
    },

    // Nueva función: Verificar si es transferencia con referencia
    _isTransferWithReference(paymentLine) {
        const method = paymentLine.payment_method;
        
        // Verificar si el método de pago es tipo transferencia/banco
        // y si ya tiene una referencia/transacción registrada
        const isTransferMethod = (
            method.type === 'bank' || 
            method.name.toLowerCase().includes('transfer') ||
            method.name.toLowerCase().includes('banco') ||
            method.name.toLowerCase().includes('deposito')
        );
        
        const hasReference = (
            paymentLine.payment_reference || 
            paymentLine.transaction_id ||
            paymentLine.card_number
        );
        
        console.log("Verificando si es transferencia con referencia:");
        console.log("  - Es método transferencia/banco:", isTransferMethod);
        console.log("  - Tiene referencia:", hasReference);
        console.log("  - Referencia:", paymentLine.payment_reference || paymentLine.transaction_id || "ninguna");
        
        return isTransferMethod && hasReference;
    },

    // Nueva función: Reemplazar método de pago
    async _replacePaymentMethod(oldPaymentLine, newPaymentMethod, authorizedBy) {
        console.log("═══════════════════════════════════════");
        console.log("REEMPLAZANDO MÉTODO DE PAGO");
        console.log("═══════════════════════════════════════");
        
        const currentOrder = this.currentOrder;
        const oldMethod = oldPaymentLine.payment_method;
        const oldAmount = oldPaymentLine.amount;
        
        console.log("Método anterior:", oldMethod.name);
        console.log("Monto anterior:", oldAmount);
        console.log("Método nuevo:", newPaymentMethod.name);
        
        // 1. Registrar el cambio en el historial
        currentOrder.add_payment_method_change(
            oldPaymentLine.cid,
            oldMethod,
            newPaymentMethod,
            authorizedBy
        );
        
        // 2. Eliminar la línea de pago anterior
        console.log("Eliminando línea de pago anterior...");
        currentOrder.remove_paymentline(oldPaymentLine);
        
        // 3. Agregar nueva línea con el mismo monto
        console.log("Agregando nueva línea de pago con monto:", oldAmount);
        const newPaymentLine = currentOrder.add_paymentline(newPaymentMethod);
        
        if (newPaymentLine) {
            // Establecer el mismo monto que tenía la línea anterior
            newPaymentLine.set_amount(oldAmount);
            console.log("✅ Nueva línea creada con monto:", newPaymentLine.amount);
        }
        
        // 4. Mostrar confirmación al usuario
        await this.popup.add(ErrorPopup, {
            title: _t("Método de Pago Cambiado"),
            body: _t(
                "El método de pago ha sido cambiado exitosamente:\n\n" +
                "Método anterior: " + oldMethod.name + "\n" +
                "Método nuevo: " + newPaymentMethod.name + "\n" +
                "Monto: " + this.env.utils.formatCurrency(oldAmount) + "\n\n" +
                "Autorizado por: " + authorizedBy
            ),
        });
        
        console.log("═══════════════════════════════════════");
        console.log("✅ MÉTODO DE PAGO REEMPLAZADO EXITOSAMENTE");
        console.log("═══════════════════════════════════════");
    },

    async _requestManagerPinAuthorization(oldMethod, newMethod) {
        console.log("═══════════════════════════════════════");
        console.log("SOLICITANDO AUTORIZACIÓN DE GERENTE");
        console.log("═══════════════════════════════════════");
        
        const { confirmed, payload: pin } = await this.popup.add(NumberPopup, {
            title: _t("Autorización de Gerente Requerida"),
            body: _t(
                "CAMBIO DE MÉTODO DE PAGO\n\n" +
                "De: " + oldMethod.name + "\n" +
                "A: " + newMethod.name + "\n\n" +
                "═════════════════════════════\n" +
                "Se requiere autorización de gerente.\n\n" +
                "Gerente/Encargado: Ingresa tu PIN:"
            ),
            startingValue: "",
            isPassword: true
        });

        if (!confirmed || !pin) {
            console.log("No se ingresó PIN");
            await this.popup.add(ErrorPopup, {
                title: _t("Cambio Cancelado"),
                body: _t(
                    "El cambio de método de pago ha sido cancelado.\n\n" +
                    "Se requiere autorización de gerente para continuar."
                ),
            });
            return { approved: false };
        }

        console.log("Validando PIN...");
        
        const validation = await this._validateManagerPin(pin);
        
        if (validation.valid) {
            console.log("PIN válido");
            return {
                approved: true,
                manager_name: validation.manager_name
            };
        } else {
            console.log("PIN inválido");
            await this.popup.add(ErrorPopup, {
                title: _t("PIN Inválido"),
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
            console.log("Validando PIN:", pin);
            
            const employees = await this.orm.searchRead(
                'hr.employee',
                [['pin', '=', String(pin)]],
                ['name', 'user_id']
            );

            if (employees.length === 0) {
                return { 
                    valid: false,
                    error_message: "No existe ningún empleado con ese PIN."
                };
            }

            const employee = employees[0];

            if (!employee.user_id || employee.user_id.length === 0) {
                return { 
                    valid: false,
                    error_message: "El empleado no tiene usuario asociado."
                };
            }

            const userId = employee.user_id[0];

            const groups = await this.orm.searchRead(
                'res.groups',
                [['name', '=', 'POS Payment Manager']],
                ['id', 'name']
            );

            if (groups.length === 0) {
                return { 
                    valid: false,
                    error_message: "Error: No se encontró el grupo de gerentes."
                };
            }

            const groupId = groups[0].id;

            const users = await this.orm.searchRead(
                'res.users',
                [['id', '=', userId]],
                ['id', 'name', 'groups_id']
            );

            if (users.length === 0) {
                return { 
                    valid: false,
                    error_message: "Error: Usuario no encontrado."
                };
            }

            const user = users[0];
            const hasGroup = user.groups_id && user.groups_id.includes(groupId);

            if (hasGroup) {
                return {
                    valid: true,
                    manager_name: employee.name
                };
            } else {
                return { 
                    valid: false,
                    error_message: "El empleado '" + employee.name + "' no tiene permisos de gerente."
                };
            }

        } catch (error) {
            console.error("ERROR validando PIN:", error);
            return { 
                valid: false,
                error_message: "Error del sistema: " + error.message
            };
        }
    },
});