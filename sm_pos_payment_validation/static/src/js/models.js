/** @odoo-module */

import { Order, Payment } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        this.payment_method_changes = this.payment_method_changes || [];
        this.initial_payment_methods = this.initial_payment_methods || {};
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.payment_method_changes = this.payment_method_changes || [];
        json.initial_payment_methods = this.initial_payment_methods || {};
        return json;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.payment_method_changes = json.payment_method_changes || [];
        this.initial_payment_methods = json.initial_payment_methods || {};
    },

    add_paymentline(payment_method) {
        const paymentline = super.add_paymentline(...arguments);
        
        if (paymentline && payment_method && !this.initial_payment_methods[paymentline.cid]) {
            this.initial_payment_methods[paymentline.cid] = payment_method.id;
        }
        
        return paymentline;
    },

    add_payment_method_change(paymentline_cid, old_method, new_method, approved_by) {
        const cashier = this.pos?.get_cashier?.() || {};
        const userName = cashier?.name || this.pos?.user?.name || 'Usuario desconocido';
        
        this.payment_method_changes.push({
            timestamp: new Date().toISOString(),
            paymentline_cid: paymentline_cid,
            old_method: old_method?.name || 'None',
            old_method_id: old_method?.id || null,
            new_method: new_method?.name || 'Unknown',
            new_method_id: new_method?.id || null,
            user: userName,
            approved_by: approved_by || null,
        });
        
        console.log("Cambio de método registrado:", this.payment_method_changes[this.payment_method_changes.length - 1]);
    },

    get_initial_payment_method(paymentline_cid) {
        return this.initial_payment_methods[paymentline_cid] || null;
    },
});

patch(Payment.prototype, {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        this.change_approved = false;
        this.approval_manager = null;
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.change_approved = this.change_approved || false;
        json.approval_manager = this.approval_manager || null;
        return json;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.change_approved = json.change_approved || false;
        this.approval_manager = json.approval_manager || null;
    },

    set_change_approved(manager_name) {
        this.change_approved = true;
        this.approval_manager = manager_name;
    },
});