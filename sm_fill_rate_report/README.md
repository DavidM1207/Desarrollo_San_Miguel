# Módulo Fill Rate Report - Requisiciones

## Descripción

Este módulo agrega un reporte dinámico de **Fill Rate** para el módulo de Requisiciones de Compra de Empleados en Odoo 17.

El Fill Rate mide el porcentaje de cumplimiento de entregas respecto a las cantidades solicitadas en las requisiciones de transferencia interna.

## Características

✅ **Reporte dinámico en Python** (sin consultas SQL directas)
✅ **Actualización automática** basada en movimientos de inventario completados
✅ **Múltiples vistas de análisis**: Lista, Pivot, Gráficos
✅ **Filtros avanzados** por fechas, rangos de Fill Rate, productos
✅ **Indicadores visuales de rendimiento**:
   - 🟢 Verde: Fill Rate ≥ 95%
   - 🟡 Amarillo: Fill Rate 70-94%
   - 🔴 Rojo: Fill Rate < 70%

## Requisitos

- Odoo 17.0
- Módulo `employee_purchase_requisition` instalado
- Módulo `stock` (inventario) instalado

## Instalación

### 1. Copiar el módulo

Copia la carpeta `fill_rate_report` a tu directorio de addons de Odoo:

```bash
cp -r fill_rate_report /path/to/odoo/addons/
```

### 2. Actualizar la lista de aplicaciones

En Odoo, ve a:
- **Aplicaciones** → **Actualizar Lista de Aplicaciones**

### 3. Instalar el módulo

Busca "Fill Rate Report" e instálalo.

## Configuración Inicial

### IMPORTANTE: Ajustes según tu implementación

El módulo asume cierta estructura de datos. Es posible que necesites ajustar lo siguiente en el archivo `models/fill_rate_report.py`:

#### 1. Relación entre Requisición y Stock Move

Busca la función `_get_delivered_quantity()` y ajusta según cómo tu módulo relaciona las requisiciones con los movimientos de inventario:

```python
# Opción 1: Si tienes un campo directo requisition_line_id en stock.move
stock_moves = self.env['stock.move'].search([
    ('requisition_line_id', '=', requisition_line.id),
    ('state', '=', 'done'),
])

# Opción 2: Si la relación es a través del picking
stock_moves = self.env['stock.move'].search([
    ('picking_id', '=', requisition_line.picking_id.id),
    ('product_id', '=', requisition_line.product_id.id),
    ('state', '=', 'done'),
])

# Opción 3: Si usas otro campo de referencia
stock_moves = self.env['stock.move'].search([
    ('origin', '=', requisition.name),
    ('product_id', '=', requisition_line.product_id.id),
    ('state', '=', 'done'),
])
```

#### 2. Campo de tipo de requisición

Asegúrate de que el campo `requisition_type` en tu modelo tenga el valor `'internal_transfer'` para transferencias internas. Si usa otro valor, actualiza la línea:

```python
if line.requisition_type != 'internal_transfer':  # Cambiar según tu implementación
    continue
```

#### 3. Campos de cantidad

El módulo asume estos campos en las líneas de requisición:
- `qty`: Cantidad solicitada
- `demand`: Demanda (opcional)

Ajusta según los nombres de campos en tu implementación.

## Uso

### Acceder al Reporte

1. Ve al módulo **Requisiciones de Compra**
2. Menú **Reportes** → **Fill Rate**

### Generar/Actualizar Datos

Los datos se generan automáticamente, pero puedes actualizarlos manualmente:

1. En la vista del reporte Fill Rate
2. Clic en **Acción** → **Actualizar Reporte Fill Rate**

### Filtros Disponibles

- **Fill Rate Bajo** (< 70%)
- **Fill Rate Medio** (70-94%)
- **Fill Rate Alto** (≥ 95%)
- **Este Mes** / **Mes Pasado** / **Este Año**

### Agrupaciones

Agrupa los datos por:
- Producto
- Requisición
- Mes de creación
- Estado

### Vistas Disponibles

1. **Lista**: Vista detallada de cada línea
2. **Pivot**: Análisis cruzado de datos
3. **Gráfico**: Visualización de tendencias

## Campos del Reporte

| Campo | Descripción |
|-------|-------------|
| **Fecha Creación** | Fecha de creación de la requisición |
| **Núm. Requisición** | Número identificador de la requisición |
| **Producto** | Producto solicitado |
| **Demanda** | Demanda registrada (si aplica) |
| **Cantidad Original** | Unidades solicitadas en la requisición |
| **Cantidad Entregada** | Unidades realmente entregadas (movimientos completados) |
| **Fill Rate (%)** | Porcentaje de cumplimiento (Entregada/Solicitada × 100) |

## Automatización (Opcional)

Para actualizar el reporte automáticamente, crea una acción programada (cron):

1. Ve a **Configuración** → **Técnico** → **Automatización** → **Acciones Programadas**
2. Crea una nueva acción:
   - **Nombre**: Actualizar Reporte Fill Rate
   - **Modelo**: fill.rate.report
   - **Tipo**: Código Python
   - **Código**:
   ```python
   model.generate_report_data()
   ```
   - **Intervalo**: Diario (o según necesites)

## Estructura del Módulo

```
fill_rate_report/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── fill_rate_report.py
├── views/
│   ├── fill_rate_report_views.xml
│   └── menu.xml
├── security/
│   └── ir.model.access.csv
└── README.md
```

## Solución de Problemas

### No aparecen datos en el reporte

1. Verifica que tienes requisiciones con tipo `'internal_transfer'`
2. Asegúrate de que los movimientos de inventario estén en estado `'done'`
3. Ejecuta manualmente: **Acción** → **Actualizar Reporte Fill Rate**
4. Revisa los logs de Odoo para errores

### Error al instalar

1. Verifica que `employee_purchase_requisition` esté instalado
2. Revisa que la ruta del módulo sea correcta
3. Verifica permisos de archivos

### Los datos no se actualizan automáticamente

Los datos se calculan al ejecutar `generate_report_data()`. Considera:
1. Llamar este método desde un trigger en requisiciones
2. Configurar un cron job
3. O actualizar manualmente cuando sea necesario

## Personalización

### Agregar campos adicionales

Edita `models/fill_rate_report.py` y añade campos según necesites:

```python
custom_field = fields.Char(string='Campo Personalizado')
```

### Modificar cálculo de Fill Rate

Ajusta el método `_compute_fill_rate()` si necesitas otra fórmula.

### Cambiar colores de indicadores

Edita las decorations en `views/fill_rate_report_views.xml`:

```xml
decoration-success="fill_rate >= 95"
decoration-warning="fill_rate >= 70 and fill_rate < 95"
decoration-danger="fill_rate < 70"
```

## Soporte

Para dudas o problemas:
- Revisa los logs de Odoo
- Verifica la configuración del módulo `employee_purchase_requisition`
- Contacta a tu equipo de desarrollo

## Licencia

LGPL-3

## Autor

Tu Empresa

## Versión

17.0.1.0.0 (Odoo 17)
