/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _t } from "@web/core/l10n/translation";
import { useState } from "@odoo/owl";

export class PasswordPopup extends AbstractAwaitablePopup {
    static template = "sm_pos_payment_validation.PasswordPopup";
    static defaultProps = {
        confirmText: _t("Ok"),
        cancelText: _t("Cancelar"),
        title: "",
        body: "",
        startingValue: "",
    };

    setup() {
        super.setup();
        this.state = useState({ 
            inputValue: this.props.startingValue
        });
    }

    // Agregar dígito al presionar botón del teclado
    appendDigit(digit) {
        this.state.inputValue = this.state.inputValue + digit.toString();
    }

    // Borrar último dígito
    deleteDigit() {
        this.state.inputValue = this.state.inputValue.slice(0, -1);
    }

    // Limpiar todo
    clearInput() {
        this.state.inputValue = "";
    }

    // Obtener valor como puntos para mostrar
    get displayValue() {
        return "●".repeat(this.state.inputValue.length);
    }

    getPayload() {
        return this.state.inputValue;
    }
}