# Product Pie Tablar (Odoo 17)

Este módulo agrega el campo **pie_tablar (Float, 4 decimales)** al modelo `product.template` y lo muestra en:
- Formulario del producto (después de `uom_id`).
- Lista de productos (después de `list_price`).

## Instalación
1. Copia la carpeta `sm_product_pie_tablar` a tu ruta de addons (por ejemplo `/odoo/custom/addons/`).
2. Reinicia el servicio de Odoo.
3. Ve a *Apps* > *Actualizar lista de aplicaciones*.
4. Instala **Product Pie Tablar**.

## Notas
- No crea modelos nuevos, por lo que no requiere reglas de acceso adicionales.
- Puedes cambiar el label del campo en `models/product_template.py` o vía traducciones.
