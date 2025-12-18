/** @odoo-module **/

import { registry } from "@web/core/registry";

// Inyectar CSS para pantalla e impresión
const style = document.createElement('style');
style.textContent = `
    .pos-receipt div:has(> :contains("Cliente:")),
    .pos-receipt div:has(> :contains("NIT:")),
    .pos-receipt div:has(> :contains("Número de recibo:")) {
        font-weight: bold !important;
        font-size: 20px !important;
    }
    
    @media print {
        .pos-receipt div {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }
    }
`;
document.head.appendChild(style);

function applyBoldStyles() {
    const divs = document.querySelectorAll('.pos-receipt div');
    divs.forEach(div => {
        const text = div.textContent;
        if (text.includes('Cliente:') || text.includes('NIT:') || text.includes('Número de recibo:')) {
            div.style.fontWeight = 'bold';
            div.style.fontSize = '20px';
            div.setAttribute('style', div.getAttribute('style') + ' font-weight: bold !important; font-size: 20px !important;');
        }
    });
}

registry.category("services").add("pos_bold_receipt", {
    start() {
        setInterval(applyBoldStyles, 2000);
    },
});