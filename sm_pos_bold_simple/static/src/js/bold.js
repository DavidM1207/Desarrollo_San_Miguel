/** @odoo-module **/

// Código que YA PROBAMOS en consola y FUNCIONÓ
function applyBold() {
    const divs = document.querySelectorAll('.pos-receipt div');
    divs.forEach(div => {
        const text = div.textContent;
        if (text.includes('Cliente:') || text.includes('NIT:') || text.includes('Número de recibo:')) {
            div.style.fontWeight = 'bold';
            div.style.fontSize = '20px';
        }
    });
}

// Ejecutar cada 2 segundos (para pantalla)
setInterval(applyBold, 2000);

// Ejecutar al cargar
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyBold);
} else {
    applyBold();
}