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
        console.log("Usuario:", this.pos.user?.name);
        
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

                const approval = await this._requestChangeAuthorization(existingMethod, paymentMethod);
                
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

    async _requestChangeAuthorization(oldMethod, newMethod) {
        console.log("═══════════════════════════════════════");
        console.log("SOLICITANDO AUTORIZACIÓN");
        console.log("═══════════════════════════════════════");
        
        const isManager = await this._checkManagerPermission();
        console.log("Usuario es gerente:", isManager);
        
        if (isManager) {
            console.log("✅ Usuario ES gerente - pidiendo PIN para confirmar");
            
            const { confirmed, payload: pin } = await this.popup.add(NumberPopup, {
                title: _t("🔐 Confirmación de Gerente"),
                body: _t(
                    "Cambio de Método de Pago:\n\n" +
                    "De: " + oldMethod.name + "\n" +
                    "A: " + newMethod.name + "\n\n" +
                    "Como gerente, ingresa tu PIN para confirmar:"
                ),
                startingValue: "",
            });

            if (!confirmed || !pin) {
                console.log("❌ Gerente canceló");
                await this.popup.add(ErrorPopup, {
                    title: _t("Cancelado"),
                    body: _t("El cambio de método de pago ha sido cancelado."),
                });
                return { approved: false };
            }

            console.log("PIN ingresado:", pin);
            const validation = await this._validateManagerPin(pin);
            console.log("Resultado de validación:", validation);
            
            if (validation.valid) {
                console.log("✅ PIN válido");
                await this.popup.add(ErrorPopup, {
                    title: _t("✅ Cambio Autorizado"),
                    body: _t("Cambio confirmado por: " + validation.manager_name),
                });
                
                return {
                    approved: true,
                    manager_name: validation.manager_name
                };
            } else {
                console.log("❌ PIN inválido o sin permisos");
                await this.popup.add(ErrorPopup, {
                    title: _t("❌ PIN Incorrecto"),
                    body: _t(
                        "El PIN ingresado no es correcto o no tiene permisos de gerente.\n\n" +
                        "Detalles:\n" +
                        validation.error_message
                    ),
                });
                return { approved: false };
            }
        }
        else {
            console.log("❌ Usuario NO es gerente");
            
            await this.popup.add(ErrorPopup, {
                title: _t("⚠️ Autorización Requerida"),
                body: _t(
                    "No tienes permisos para cambiar el método de pago.\n\n" +
                    "Se requiere la autorización de un gerente o supervisor.\n\n" +
                    "Por favor, llama a un gerente."
                ),
            });
            
            const { confirmed, payload: pin } = await this.popup.add(NumberPopup, {
                title: _t("🔐 PIN de Gerente Requerido"),
                body: _t(
                    "CAMBIO DE MÉTODO DE PAGO\n\n" +
                    "De: " + oldMethod.name + "\n" +
                    "A: " + newMethod.name + "\n\n" +
                    "Gerente: Ingresa tu PIN para autorizar:"
                ),
                startingValue: "",
            });

            if (!confirmed || !pin) {
                console.log("❌ No se ingresó PIN");
                await this.popup.add(ErrorPopup, {
                    title: _t("❌ Cambio Bloqueado"),
                    body: _t("El cambio ha sido bloqueado. Se requiere autorización."),
                });
                return { approved: false };
            }

            const validation = await this._validateManagerPin(pin);
            
            if (validation.valid) {
                console.log("✅ PIN de gerente válido");
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
                        "El PIN ingresado no es válido o no tiene permisos.\n\n" +
                        "Detalles:\n" +
                        validation.error_message
                    ),
                });
                return { approved: false };
            }
        }
    },

    async _checkManagerPermission() {
        try {
            const userId = this.pos.user?.id;
            
            if (!userId) {
                console.error("❌ No hay user ID");
                return false;
            }
            
            console.log("═══════════════════════════════════════");
            console.log("VERIFICANDO PERMISOS");
            console.log("User ID:", userId);
            console.log("User name:", this.pos.user?.name);
            console.log("Group a verificar: sm_pos_payment_validation.group_pos_payment_manager");
            
            const result = await this.orm.call(
                'res.users',
                'has_group',
                [userId, 'sm_pos_payment_validation.group_pos_payment_manager']
            );
            
            console.log("RESULTADO:", result ? "✅ SÍ TIENE PERMISO" : "❌ NO TIENE PERMISO");
            console.log("═══════════════════════════════════════");
            
            return result;
            
        } catch (error) {
            console.error("❌ Error verificando permisos:", error);
            return false;
        }
    },

    async _validateManagerPin(pin) {
        try {
            console.log("═══════════════════════════════════════");
            console.log("VALIDANDO PIN DE GERENTE");
            console.log("PIN recibido:", pin);
            console.log("Tipo de PIN:", typeof pin);
            console.log("═══════════════════════════════════════");
            
            // Buscar empleado por PIN
            console.log("1. Buscando empleado con PIN:", pin);
            const employees = await this.orm.searchRead(
                'hr.employee',
                [['pin', '=', String(pin)]],
                ['name', 'user_id', 'pin']
            );

            console.log("2. Empleados encontrados:", employees.length);
            
            if (employees.length === 0) {
                console.log("❌ No se encontró ningún empleado con ese PIN");
                return { 
                    valid: false,
                    error_message: "No se encontró empleado con ese PIN"
                };
            }

            const employee = employees[0];
            console.log("3. Empleado encontrado:");
            console.log("   - Nombre:", employee.name);
            console.log("   - PIN guardado:", employee.pin);
            console.log("   - User ID:", employee.user_id);

            if (!employee.user_id || employee.user_id.length === 0) {
                console.log("❌ El empleado NO tiene usuario asociado");
                return { 
                    valid: false,
                    error_message: "El empleado '" + employee.name + "' no tiene usuario asociado en el sistema"
                };
            }

            const userId = employee.user_id[0];
            console.log("4. User ID del empleado:", userId);

            // Verificar permisos del usuario
            console.log("5. Verificando si el usuario tiene permisos de gerente...");
            const hasPermission = await this.orm.call(
                'res.users',
                'has_group',
                [userId, 'sm_pos_payment_validation.group_pos_payment_manager']
            );

            console.log("6. ¿Tiene permisos de gerente?:", hasPermission);

            if (hasPermission) {
                console.log("✅ PIN VÁLIDO - Usuario tiene permisos de gerente");
                console.log("═══════════════════════════════════════");
                return {
                    valid: true,
                    manager_name: employee.name
                };
            } else {
                console.log("❌ El empleado existe pero NO tiene permisos de gerente");
                console.log("═══════════════════════════════════════");
                return { 
                    valid: false,
                    error_message: "El empleado '" + employee.name + "' no tiene permisos de gerente"
                };
            }

        } catch (error) {
            console.error("❌ ERROR validando PIN:", error);
            console.error("Mensaje:", error.message);
            console.error("Stack:", error.stack);
            return { 
                valid: false,
                error_message: "Error del sistema: " + error.message
            };
        }
    },
});