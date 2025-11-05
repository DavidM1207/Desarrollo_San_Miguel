/** @odoo-module **/

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(Order.prototype, {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        this.to_ship = true;
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

    get_shipping_date() {
        if (this.shipping_date) {
            return this.shipping_date;
        }
        const today = new Date();
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, '0');
        const day = String(today.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
});

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.currentOrder) {
            this.currentOrder.to_ship = true;
            const today = new Date();
            const year = today.getFullYear();
            const month = String(today.getMonth() + 1).padStart(2, '0');
            const day = String(today.getDate()).padStart(2, '0');
            this.currentOrder.shipping_date = `${year}-${month}-${day}`;
        }
    }
});