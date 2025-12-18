/* Estilos para resaltar Cliente, NIT y Número de Orden en el recibo del POS */

/* ===================================
   NOMBRE DEL CLIENTE - MUY DESTACADO
   =================================== */

/* Contenedor completo de información del cliente */
.pos-receipt .pos-receipt-contact {
    font-weight: bold !important;
    font-size: 20px !important;
    margin: 15px 0 !important;
    padding: 10px 0 !important;
    border-top: 2px solid #000 !important;
    border-bottom: 2px solid #000 !important;
    background-color: #f5f5f5 !important;
}

/* Nombre específico del cliente */
.pos-receipt .pos-receipt-contact .client-name,
.pos-receipt .pos-receipt-contact [class*="client-name"],
.pos-receipt .pos-receipt-contact .col-auto {
    font-weight: bold !important;
    font-size: 22px !important;
    color: #000 !important;
}

/* ===================================
   NIT DEL CLIENTE - EN NEGRILLA
   =================================== */

/* NIT, Tax ID, RFC o cualquier identificación fiscal */
.pos-receipt .pos-receipt-contact .client-vat,
.pos-receipt .pos-receipt-contact [class*="vat"],
.pos-receipt .pos-receipt-contact [class*="tax-id"],
.pos-receipt .pos-receipt-contact div:contains("NIT"),
.pos-receipt .pos-receipt-contact div:contains("Tax ID"),
.pos-receipt .pos-receipt-contact div:contains("RFC") {
    font-weight: bold !important;
    font-size: 18px !important;
    color: #000 !important;
    margin: 5px 0 !important;
}

/* Buscar específicamente el texto del NIT */
.pos-receipt .pos-receipt-contact div {
    font-weight: inherit;
}

.pos-receipt .pos-receipt-contact div strong,
.pos-receipt .pos-receipt-contact div b {
    font-weight: bold !important;
    font-size: 18px !important;
}

/* ===================================
   NÚMERO DE ORDEN - EN NEGRILLA
   =================================== */

/* Contenedor de datos de la orden */
.pos-receipt .pos-receipt-order-data {
    font-weight: bold !important;
    font-size: 18px !important;
    margin: 15px 0 !important;
    padding: 10px 0 !important;
    border-top: 2px solid #000 !important;
    background-color: #f5f5f5 !important;
}

/* Número de orden específico */
.pos-receipt .pos-receipt-order-data .order-name,
.pos-receipt .pos-receipt-order-data [class*="order-name"],
.pos-receipt .pos-receipt-order-data [class*="order-ref"],
.pos-receipt .pos-receipt-order-data .pos-order-ref {
    font-weight: bold !important;
    font-size: 20px !important;
    color: #000 !important;
}

/* Si el número de orden está en un div específico */
.pos-receipt .pos-receipt-order-data div:first-child,
.pos-receipt .order-reference {
    font-weight: bold !important;
    font-size: 20px !important;
}

/* ===================================
   ESTILOS ADICIONALES PARA MEJORAR VISIBILIDAD
   =================================== */

/* Asegurar que todo el texto dentro de estos elementos sea visible */
.pos-receipt .pos-receipt-contact *,
.pos-receipt .pos-receipt-order-data * {
    font-weight: bold !important;
}

/* Mejorar el contraste en impresión */
@media print {
    .pos-receipt .pos-receipt-contact,
    .pos-receipt .pos-receipt-order-data {
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
        color: #000 !important;
    }
}

/* ===================================
   OPCIONAL: Si quieres aún más destacado
   =================================== */

/* Descomentar estas líneas si quieres que sea MUY visible */
/*
.pos-receipt .pos-receipt-contact {
    background-color: #ffeb3b !important;
    padding: 15px !important;
}

.pos-receipt .pos-receipt-order-data {
    background-color: #e3f2fd !important;
    padding: 15px !important;
}
*/