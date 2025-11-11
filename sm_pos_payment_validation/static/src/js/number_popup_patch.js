/** @odoo-module */

import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { patch } from "@web/core/utils/patch";

patch(NumberPopup.prototype, {
    setup() {
        super.setup(...arguments);
    },

    // Interceptar el valor mostrado para convertirlo en puntos
    get displayValue() {
        // Si el popup tiene la propiedad isPassword, mostrar puntos
        if (this.props.isPassword && this.state.buffer) {
            return "●".repeat(this.state.buffer.length);
        }
        // Si no, comportamiento normal
        return super.displayValue;
    }
});