/** @odoo-module **/

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

// Patch del modelo Order para forzar to_ship
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

// Patch de PaymentScreen para activar el botón visualmente
patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        // Forzar shipping al montar la pantalla
        if (this.currentOrder) {
            this.currentOrder.to_ship = true;
            const today = new Date();
            const year = today.getFullYear();
            const month = String(today.getMonth() + 1).padStart(2, '0');
            const day = String(today.getDate()).padStart(2, '0');
            this.currentOrder.shipping_date = `${year}-${month}-${day}`;
        }
    },

    async _onMounted() {
        if (super._onMounted) {
            await super._onMounted();
        }
        // Asegurar que el estado se mantiene
        if (this.currentOrder) {
            this.currentOrder.to_ship = true;
            if (!this.currentOrder.shipping_date) {
                const today = new Date();
                const year = today.getFullYear();
                const month = String(today.getMonth() + 1).padStart(2, '0');
                const day = String(today.getDate()).padStart(2, '0');
                this.currentOrder.shipping_date = `${year}-${month}-${day}`;
            }
        }
    }
});
