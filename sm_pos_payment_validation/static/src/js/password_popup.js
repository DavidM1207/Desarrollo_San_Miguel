/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _t } from "@web/core/l10n/translation";
import { useState } from "@odoo/owl";

export class PasswordPopup extends AbstractAwaitablePopup {
    static template = "sm_pos_payment_validation.PasswordPopup";
    static defaultProps = {
        confirmText: _t("Confirmar"),
        cancelText: _t("Cancelar"),
        title: "",
        body: "",
        startingValue: "",
    };

    setup() {
        super.setup();
        this.state = useState({ 
            inputValue: this.props.startingValue,
            displayValue: ""
        });
    }

    onInputChange(event) {
        const value = event.target.value;
        this.state.inputValue = value;
        // Mostrar puntos en lugar de números
        this.state.displayValue = "●".repeat(value.length);
    }

    getPayload() {
        return this.state.inputValue;
    }
}