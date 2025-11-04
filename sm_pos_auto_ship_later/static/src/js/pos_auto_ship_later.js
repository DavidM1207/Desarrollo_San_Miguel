/** @odoo-module **/

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

// Extender el modelo Order para forzar ship_later
patch(Order.prototype, {
    
    /**
     * Modificar el método export_as_JSON para incluir 
     * automáticamente to_ship y shipping_date
     */
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        
        // Forzar que siempre tenga to_ship en true
        json.to_ship = true;
        
        // Establecer la fecha de envío como la fecha actual
        const today = new Date();
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, '0');
        const day = String(today.getDate()).padStart(2, '0');
        json.shipping_date = `${year}-${month}-${day}`;
        
        return json;
    },

    /**
     * Asegurar que al exportar para la UI también tenga los valores correctos
     */
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        result.to_ship = true;
        result.shipping_date = new Date().toISOString().split('T')[0];
        return result;
    }
});
