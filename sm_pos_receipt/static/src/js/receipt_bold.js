/** @odoo-module **/

// Inyectar estilos cuando se carga el POS
const style = document.createElement('style');
style.textContent = `
    /* Cliente en negrilla */
    .pos-receipt-container div div div:nth-child(1) {
        font-weight: bold !important;
        font-size: 20px !important;
    }
    
    /* Líneas con Cliente y NIT */
    .pos-receipt div div:has(div:first-child) {
        font-weight: bold !important;
    }
`;

document.head.appendChild(style);

// Observar cuando se renderiza el recibo
const observer = new MutationObserver(() => {
    const receipt = document.querySelector('.pos-receipt-container');
    if (receipt) {
        const divs = receipt.querySelectorAll('div');
        divs.forEach(div => {
            const text = div.textContent.trim();
            if (text.includes('Cliente:') || text.includes('NIT:') || text.includes('Número de recibo:')) {
                div.style.fontWeight = 'bold';
                div.style.fontSize = '20px';
            }
        });
    }
});

// Iniciar observador cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        observer.observe(document.body, { childList: true, subtree: true });
    });
} else {
    observer.observe(document.body, { childList: true, subtree: true });
}