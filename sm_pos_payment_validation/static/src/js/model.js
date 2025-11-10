/** @odoo-module */

import { Order, Payment } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        this.payment_method_changes = this.payment_method_changes || [];
        this.initial_payment_method_set = false;
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.payment_method_changes = this.payment_method_changes;
        return json;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.payment_method_changes = json.payment_method_changes || [];
    },

    add_payment_method_change(old_method, new_method, approved_by) {
        this.payment_method_changes.push({
            timestamp: new Date().toISOString(),
            old_method: old_method ? old_method.name : 'None',
            new_method: new_method.name,
            user: this.pos.get_cashier().name,
            approved_by: approved_by || null,
        });
    },

    get_payment_method_changes() {
        return this.payment_method_changes;
    },
});

patch(Payment.prototype, {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        this.original_payment_method_id = this.payment_method_id;
        this.change_approved = false;
        this.approval_manager = null;
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.original_payment_method_id = this.original_payment_method_id;
        json.change_approved = this.change_approved;
        json.approval_manager = this.approval_manager;
        return json;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.original_payment_method_id = json.original_payment_method_id;
        this.change_approved = json.change_approved || false;
        this.approval_manager = json.approval_manager || null;
    },

    set_payment_method(payment_method) {
        const old_method = this.payment_method;
        super.set_payment_method(...arguments);
        
        // Si ya tenía un método de pago y se está cambiando
        if (old_method && old_method.id !== payment_method.id) {
            this.payment_method_changed = true;
            this.original_payment_method_id = old_method.id;
        }
    },

    get_payment_method_changed() {
        return this.payment_method_changed || false;
    },

    approve_change(manager_pin) {
        this.change_approved = true;
        this.approval_manager = manager_pin;
    },
});