odoo.define("pt_nit_verification.ClientDetailEdit", function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    const PartnerDetailsEdit = require('point_of_sale.PartnerDetailsEdit')
    const Registries = require('point_of_sale.Registries');

    const ClientEdit = (PartnerDetailsEdit) =>
        class extends PartnerDetailsEdit {
            constructor() {
                super(...arguments);
            }
            saveChanges() {
                let processedChanges = {};
                for (let [key, value] of Object.entries(this.changes)) {
                    if (this.intFields.includes(key)) {
                        processedChanges[key] = parseInt(value) || false;
                    } else {
                        processedChanges[key] = value;
                    }
                }
                if ((!this.props.partner.name && !processedChanges.name) ||
                    processedChanges.name === '' ){
                        processedChanges.name = '-';
                        this.props.partner.name = '-'
                }
                super.saveChanges();
            }
        };
        
    Registries.Component.extend(PartnerDetailsEdit, ClientEdit);

    return ClientEdit;
});