/** @odoo-module **/

import { registry } from "@web/core/registry";

// Función para aplicar negrilla
function applyBoldStyles() {
    const divs = document.querySelectorAll('.pos-receipt div');
    divs.forEach(div => {
        const text = div.textContent;
        if (text.includes('Cliente:') || text.includes('NIT:') || text.includes('Número de recibo:')) {
            div.style.fontWeight = 'bold';
            div.style.fontSize = '20px';
        }
    });
}

// Ejecutar cuando el DOM cambie
const observer = new MutationObserver(() => {
    if (document.querySelector('.pos-receipt')) {
        applyBoldStyles();
    }
});

// Iniciar observador
observer.observe(document.body, { 
    childList: true, 
    subtree: true 
});

// También ejecutar al cargar
setTimeout(applyBoldStyles, 1000);

// Registrar como servicio
registry.category("services").add("pos_bold_receipt", {
    start() {
        setInterval(applyBoldStyles, 2000);
    },
});