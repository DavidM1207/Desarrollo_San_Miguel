/** @odoo-module **/

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        // Forzar que to_ship esté marcado desde el inicio
        this.to_ship = true;
        // Establecer la fecha actual
        const today = new Date();
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, '0');
        const day = String(today.getDate()).padStart(2, '0');
        this.shipping_date = `${year}-${month}-${day}`;
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.to_ship = true;
        const today = new Date();
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, '0');
        const day = String(today.getDate()).padStart(2, '0');
        json.shipping_date = `${year}-${month}-${day}`;
        return json;
    },

    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        result.to_ship = true;
        result.shipping_date = new Date().toISOString().split('T')[0];
        return result;
    }
});