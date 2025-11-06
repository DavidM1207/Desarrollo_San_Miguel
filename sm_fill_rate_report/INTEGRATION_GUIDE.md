# Guía de Integración - Fill Rate Report

## Introducción

Esta guía te ayudará a integrar el módulo Fill Rate Report con tu módulo existente `employee_purchase_requisition`. El módulo está diseñado para ser flexible, pero requiere algunos ajustes según tu implementación específica.

## ⚠️ Puntos Críticos de Integración

### 1. Relación Requisición ↔ Stock Move

**El punto más importante es cómo tu módulo relaciona las líneas de requisición con los movimientos de inventario.**

#### Escenario A: Campo Directo en stock.move

Si tu módulo agrega un campo `requisition_line_id` directamente en el modelo `stock.move`:

```python
# En tu módulo employee_purchase_requisition
class StockMove(models.Model):
    _inherit = 'stock.move'
    
    requisition_line_id = fields.Many2one('employee.purchase.requisition.order', ...)
```

✅ **No necesitas cambios** en el código del Fill Rate Report. Ya está preparado para esto.

#### Escenario B: Relación a través de Picking

Si la relación es a través del `picking_id`:

```python
# En models/fill_rate_report.py, método _get_delivered_quantity
# Reemplazar:
stock_moves = self.env['stock.move'].search([
    ('requisition_line_id', '=', requisition_line.id),
    ('state', '=', 'done'),
])

# Por:
if hasattr(requisition_line, 'picking_id') and requisition_line.picking_id:
    stock_moves = self.env['stock.move'].search([
        ('picking_id', '=', requisition_line.picking_id.id),
        ('product_id', '=', requisition_line.product_id.id),
        ('state', '=', 'done'),
    ])
```

#### Escenario C: Relación por Referencia/Origin

Si usas el campo `origin` en stock.move:

```python
# En models/fill_rate_report.py, método _get_delivered_quantity
stock_moves = self.env['stock.move'].search([
    ('origin', '=', requisition_line.requisition_id.name),
    ('product_id', '=', requisition_line.product_id.id),
    ('state', '=', 'done'),
])
```

### 2. Tipo de Requisición (requisition_type)

Identifica qué valor usa tu módulo para las transferencias internas:

```python
# Valores comunes:
# 'internal_transfer'
# 'internal'
# 'transfer'
# 'stock_transfer'
```

**Dónde cambiar:**

```python
# En models/fill_rate_report.py, método generate_report_data
# Línea ~66
if line.requisition_type != 'internal_transfer':  # ← CAMBIAR AQUÍ
    continue
```

**Cómo verificar el valor correcto:**

```python
# En shell de Odoo:
requisition = env['employee.purchase.requisition'].search([], limit=1)
for line in requisition.requisition_order_ids:
    print(f"Line: {line.id}, Type: {line.requisition_type}")
```

### 3. Campos de Cantidad en Línea de Requisición

Verifica los nombres de los campos en tu modelo `employee.purchase.requisition.order`:

```python
# Campos comunes:
# - qty (cantidad)
# - product_qty (cantidad de producto)
# - quantity (cantidad)
# - demand (demanda)
```

**Dónde cambiar:**

```python
# En models/fill_rate_report.py, método generate_report_data
# Líneas ~71-75
data = {
    'demand': line.demand if hasattr(line, 'demand') else line.qty,  # ← VERIFICAR
    'qty_original': line.qty,  # ← VERIFICAR nombre del campo
    ...
}
```

### 4. Modelo de Línea de Requisición

Verifica el nombre exacto del modelo de líneas:

```python
# Puede ser:
# 'employee.purchase.requisition.order'
# 'employee.purchase.requisition.line'
# 'purchase.requisition.line'
```

**Dónde verificar/cambiar:**

```python
# En models/fill_rate_report.py
requisition_line_id = fields.Many2one(
    'employee.purchase.requisition.order',  # ← VERIFICAR NOMBRE
    ...
)
```

## 🔍 Verificación de Integración

### Paso 1: Verificar Estructura de Datos

Ejecuta en shell de Odoo:

```python
# 1. Verificar modelo de requisición
Requisition = env['employee.purchase.requisition']
req = Requisition.search([], limit=1)
print(f"Requisición: {req.name}")

# 2. Verificar líneas
for line in req.requisition_order_ids:
    print(f"Línea: {line.id}")
    print(f"  - Producto: {line.product_id.name}")
    print(f"  - Tipo: {line.requisition_type}")
    print(f"  - Cantidad: {line.qty}")  # Verificar nombre del campo
    
    # 3. Verificar relación con stock.move
    if hasattr(line, 'requisition_line_id'):
        moves = env['stock.move'].search([('requisition_line_id', '=', line.id)])
        print(f"  - Movimientos encontrados: {len(moves)}")
    elif hasattr(line, 'picking_id'):
        print(f"  - Picking: {line.picking_id.name if line.picking_id else 'No'}")
```

### Paso 2: Verificar Movimientos de Inventario

```python
# Buscar un movimiento relacionado con requisición
Move = env['stock.move']
moves = Move.search([('state', '=', 'done')], limit=10)

for move in moves:
    # Verificar si tiene relación con requisición
    if hasattr(move, 'requisition_line_id') and move.requisition_line_id:
        print(f"Movimiento {move.id} relacionado con requisición")
        print(f"  - Origen: {move.origin}")
        print(f"  - Cantidad: {move.product_uom_qty}")
        print(f"  - Hecho: {move.quantity_done}")
```

### Paso 3: Probar Generación Manual

```python
# Generar datos del reporte
FillRate = env['fill.rate.report']
FillRate.generate_report_data()

# Verificar resultados
reports = FillRate.search([])
print(f"Registros generados: {len(reports)}")

for report in reports[:5]:
    print(f"\nRequisición: {report.requisition_number}")
    print(f"  Producto: {report.product_name}")
    print(f"  Solicitado: {report.qty_original}")
    print(f"  Entregado: {report.qty_delivered}")
    print(f"  Fill Rate: {report.fill_rate}%")
```

## 🛠️ Ajustes Comunes

### Ajuste 1: Agregar Filtro por Almacén

Si necesitas filtrar por almacén de destino:

```python
# En models/fill_rate_report.py, agregar campo:
warehouse_id = fields.Many2one('stock.warehouse', string='Almacén', readonly=True)

# En método generate_report_data, agregar al data:
'warehouse_id': line.warehouse_id.id if hasattr(line, 'warehouse_id') else False,
```

### Ajuste 2: Agregar Estado de Requisición

```python
# Ya está incluido, pero puedes hacer filtros adicionales:
# En generate_report_data, después de la línea requisitions = ...

requisitions = self.env['employee.purchase.requisition'].search([
    ('state', 'in', ['approved', 'done']),  # Solo aprobadas/completadas
])
```

### Ajuste 3: Considerar Cancelaciones

```python
# En método _get_delivered_quantity:
stock_moves = self.env['stock.move'].search([
    ('requisition_line_id', '=', requisition_line.id),
    ('state', 'in', ['done', 'cancel']),  # Incluir cancelados si es necesario
])

# Sumar solo los 'done'
for move in stock_moves:
    if move.state == 'done':
        qty_delivered += move.quantity_done or move.product_uom_qty
```

### Ajuste 4: Manejar Múltiples Pickings por Línea

```python
# Si una línea puede generar múltiples pickings:
def _get_delivered_quantity(self, requisition_line):
    qty_delivered = 0.0
    
    # Buscar todos los pickings relacionados
    pickings = self.env['stock.picking'].search([
        ('origin', '=', requisition_line.requisition_id.name),
        ('state', '=', 'done'),
    ])
    
    for picking in pickings:
        moves = picking.move_ids_without_package.filtered(
            lambda m: m.product_id == requisition_line.product_id
        )
        for move in moves:
            qty_delivered += move.quantity_done or move.product_uom_qty
    
    return qty_delivered
```

## 🔄 Actualización Automática

### Opción 1: Trigger en Requisición (Recomendado)

Modifica tu módulo `employee_purchase_requisition`:

```python
# En models/employee_purchase_requisition.py

def write(self, vals):
    res = super().write(vals)
    
    # Si cambia el estado a 'done', actualizar Fill Rate
    if 'state' in vals and vals['state'] == 'done':
        self.env['fill.rate.report'].generate_report_data()
    
    return res
```

### Opción 2: Cron Job

Crea una acción programada en Odoo:

```xml
<!-- En data/cron.xml -->
<record id="ir_cron_update_fill_rate" model="ir.cron">
    <field name="name">Actualizar Reporte Fill Rate</field>
    <field name="model_id" ref="model_fill_rate_report"/>
    <field name="state">code</field>
    <field name="code">model.generate_report_data()</field>
    <field name="interval_number">1</field>
    <field name="interval_type">days</field>
    <field name="numbercall">-1</field>
    <field name="active">True</field>
</record>
```

### Opción 3: Actualización Automática con Stock Move (Ya incluida)

El archivo `models/stock_move_inherit.py` ya incluye esta funcionalidad. Se actualiza automáticamente cuando:
- Se completa un movimiento de inventario (`_action_done`)
- Se valida un picking (`button_validate`)

## 📊 Personalización de Vistas

### Agregar Campo Personalizado a la Vista

```xml
<!-- En views/fill_rate_report_views.xml -->
<field name="qty_original" string="Cantidad Original (Solicitada)"/>
<field name="custom_field" string="Mi Campo"/>  <!-- AGREGAR AQUÍ -->
<field name="qty_delivered" string="Cantidad Entregada"/>
```

### Cambiar Rangos de Color

```xml
<!-- Cambiar de 95/70 a 90/60 -->
<tree ... 
      decoration-success="fill_rate &gt;= 90"
      decoration-warning="fill_rate &gt;= 60 and fill_rate &lt; 90"
      decoration-danger="fill_rate &lt; 60">
```

## 🐛 Troubleshooting

### Problema: No aparecen datos

**Causas posibles:**
1. No hay requisiciones de tipo `internal_transfer`
2. Los movimientos no están en estado `done`
3. La relación requisición ↔ stock.move no está correcta

**Solución:**
- Ejecutar verificación (ver Paso 1-3 arriba)
- Revisar logs de Odoo
- Verificar configuración de tipos de requisición

### Problema: Cantidades incorrectas

**Causas posibles:**
1. Campo de cantidad mal identificado
2. Unidades de medida diferentes
3. Movimientos duplicados

**Solución:**
```python
# Agregar conversión de unidades de medida
qty_delivered = 0.0
for move in stock_moves:
    qty = move.quantity_done or move.product_uom_qty
    # Convertir a UdM del producto
    qty_delivered += move.product_uom._compute_quantity(
        qty, 
        requisition_line.product_id.uom_id
    )
```

### Problema: Error al instalar

**Error común:** `Model not found: employee.purchase.requisition.order`

**Solución:** Verifica el nombre exacto del modelo en tu implementación.

## 📞 Checklist de Integración

- [ ] Identificar tipo de relación requisición ↔ stock.move
- [ ] Verificar valor de `requisition_type` para transferencias internas
- [ ] Confirmar nombres de campos de cantidad
- [ ] Verificar nombre del modelo de líneas de requisición
- [ ] Probar generación manual del reporte
- [ ] Configurar actualización automática (cron o trigger)
- [ ] Verificar permisos de acceso
- [ ] Probar con datos reales
- [ ] Documentar configuración específica

## 🎯 Próximos Pasos

1. Seguir los pasos de verificación
2. Hacer los ajustes necesarios según tu implementación
3. Probar en entorno de desarrollo
4. Desplegar a producción
5. Configurar actualización automática

¿Necesitas ayuda adicional? Revisa el README.md principal o contacta a tu equipo de desarrollo.
