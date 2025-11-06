# 🚀 Instalación Rápida - Fill Rate Report

## 📦 Estructura del Módulo Completo

```
fill_rate_report/
├── __init__.py                              # Inicialización principal
├── __manifest__.py                          # Manifest del módulo
├── README.md                                # Documentación general
├── INTEGRATION_GUIDE.md                     # Guía de integración detallada
├── QUICK_INSTALL.md                         # Este archivo
│
├── models/                                  # Modelos de datos
│   ├── __init__.py
│   ├── fill_rate_report.py                 # Modelo principal del reporte
│   └── stock_move_inherit.py               # Actualización automática
│
├── views/                                   # Vistas XML
│   ├── fill_rate_report_views.xml          # Vistas del reporte
│   └── menu.xml                             # Menús
│
├── wizard/                                  # Asistentes
│   ├── __init__.py
│   ├── fill_rate_diagnostic_wizard.py      # Wizard de diagnóstico
│   └── fill_rate_diagnostic_wizard_views.xml
│
└── security/                                # Seguridad y permisos
    └── ir.model.access.csv                 # Permisos de acceso
```

## ⚡ Instalación en 5 Pasos

### 1️⃣ Copiar el Módulo

```bash
# Copiar toda la carpeta al directorio de addons
cp -r fill_rate_report /path/to/odoo/addons/

# O crear un symlink
ln -s /path/to/fill_rate_report /path/to/odoo/addons/
```

### 2️⃣ Actualizar Permisos

```bash
# Asegurar permisos correctos
chmod -R 755 fill_rate_report/
chown -R odoo:odoo fill_rate_report/
```

### 3️⃣ Reiniciar Odoo

```bash
# Reiniciar el servicio de Odoo
sudo systemctl restart odoo

# O si usas el comando directo
./odoo-bin -c /path/to/odoo.conf --stop-after-init -u all
```

### 4️⃣ Actualizar Lista de Aplicaciones

En la interfaz de Odoo:
1. Ve a **Aplicaciones**
2. Clic en **⋮** (tres puntos)
3. Clic en **Actualizar Lista de Aplicaciones**
4. Confirma la actualización

### 5️⃣ Instalar el Módulo

1. En **Aplicaciones**, busca: `Fill Rate`
2. Clic en **Instalar**
3. Espera a que se complete la instalación

## ✅ Verificación Post-Instalación

### Verificar Menú

1. Ve al módulo **Requisiciones de Compra**
2. Deberías ver el nuevo menú **Reportes**
3. Dentro, deberías ver:
   - **Fill Rate**
   - **Asistente de Diagnóstico**

### Ejecutar Diagnóstico

1. Ve a **Reportes** → **Asistente de Diagnóstico**
2. Selecciona **Ejecutar Diagnóstico**
3. Clic en **Ejecutar**
4. Revisa los resultados:
   - ✅ Verde = Todo OK
   - ⚠️ Amarillo = Advertencia (revisar)
   - ❌ Rojo = Error (requiere acción)

### Generar Datos Iniciales

Si el diagnóstico está OK:

1. En el mismo asistente, selecciona **Generar Datos del Reporte**
2. Clic en **Ejecutar**
3. Ve a **Reportes** → **Fill Rate** para ver los datos

## 🔧 Configuración Inicial

### Ajuste 1: Tipo de Requisición (CRÍTICO)

El módulo busca requisiciones con `requisition_type = 'internal_transfer'`.

**Si tu sistema usa otro valor:**

Edita `models/fill_rate_report.py`, línea ~66:

```python
# ANTES
if line.requisition_type != 'internal_transfer':
    continue

# DESPUÉS (ejemplo si usas 'internal')
if line.requisition_type != 'internal':
    continue
```

**¿Cómo saber qué valor usar?**

Ejecuta en shell de Odoo:
```python
req = env['employee.purchase.requisition'].search([], limit=1)
for line in req.requisition_order_ids:
    print(f"Tipo: {line.requisition_type}")
```

### Ajuste 2: Relación con Stock Move

**Escenario A: Campo directo (recomendado)**

Si tienes `requisition_line_id` en `stock.move`:
✅ No necesitas cambios

**Escenario B: Relación por picking**

Edita `models/fill_rate_report.py`, método `_get_delivered_quantity`:

```python
def _get_delivered_quantity(self, requisition_line):
    qty_delivered = 0.0
    
    if hasattr(requisition_line, 'picking_id') and requisition_line.picking_id:
        stock_moves = self.env['stock.move'].search([
            ('picking_id', '=', requisition_line.picking_id.id),
            ('product_id', '=', requisition_line.product_id.id),
            ('state', '=', 'done'),
        ])
        
        for move in stock_moves:
            qty_delivered += move.quantity_done or move.product_uom_qty
    
    return qty_delivered
```

### Ajuste 3: Nombres de Campos de Cantidad

Si tu módulo usa nombres diferentes para los campos de cantidad:

Edita `models/fill_rate_report.py`, método `generate_report_data`, línea ~73:

```python
# Ejemplo si usas 'product_qty' en lugar de 'qty'
data = {
    ...
    'qty_original': line.product_qty,  # Cambiar según tu campo
    ...
}
```

## 🎯 Primeros Pasos

### 1. Crear Requisiciones de Prueba

1. Crea una requisición con tipo "Transferencia Interna"
2. Agrega algunos productos
3. Genera los movimientos de inventario
4. Valida los pickings (márcalos como "Hecho")

### 2. Actualizar Reporte

Opción A: **Automático**
- Los datos se actualizan automáticamente al completar movimientos

Opción B: **Manual**
1. Ve a **Reportes** → **Fill Rate**
2. Clic en **Acción** → **Actualizar Reporte Fill Rate**

### 3. Explorar el Reporte

- **Vista Lista**: Detalle de cada línea
- **Vista Pivot**: Análisis cruzado
- **Vista Gráfico**: Tendencias visuales

## 📊 Interpretación del Fill Rate

| Color | Rango | Significado |
|-------|-------|-------------|
| 🟢 Verde | ≥ 95% | Excelente cumplimiento |
| 🟡 Amarillo | 70-94% | Cumplimiento aceptable |
| 🔴 Rojo | < 70% | Requiere atención |

**Fórmula:**
```
Fill Rate = (Cantidad Entregada / Cantidad Solicitada) × 100
```

## 🔄 Automatización

### Opción 1: Actualización Automática (Ya incluida)

El archivo `models/stock_move_inherit.py` actualiza automáticamente cuando:
- Se completa un movimiento (`_action_done`)
- Se valida un picking (`button_validate`)

✅ **Recomendado**: Dejar esta opción activa

### Opción 2: Cron Job

Para actualización periódica completa:

1. Ve a **Configuración** → **Técnico** → **Automatización** → **Acciones Programadas**
2. Crear nueva:
   - **Nombre**: Actualizar Fill Rate
   - **Modelo**: fill.rate.report
   - **Código**: `model.generate_report_data()`
   - **Intervalo**: Diario a las 2:00 AM

## 🐛 Solución de Problemas Comunes

### ❌ Error: "Model not found: employee.purchase.requisition"

**Causa**: Módulo `employee_purchase_requisition` no instalado

**Solución**:
```bash
# Instalar dependencias
odoo-bin -d tu_base_datos -i employee_purchase_requisition
```

### ❌ No aparecen datos en el reporte

**Diagnóstico**:
1. Ejecuta **Asistente de Diagnóstico**
2. Verifica puntos marcados en ⚠️ o ❌
3. Revisa los ajustes de configuración (ver arriba)

**Soluciones comunes**:
- Verificar que existan requisiciones de tipo "internal_transfer"
- Verificar que haya movimientos en estado "done"
- Ejecutar manualmente "Generar Datos del Reporte"

### ❌ Error al calcular cantidades

**Causa**: Unidades de medida diferentes

**Solución**: Agregar conversión de UdM en `_get_delivered_quantity`:
```python
qty_delivered += move.product_uom._compute_quantity(
    qty, 
    requisition_line.product_id.uom_id
)
```

### ❌ Permisos insuficientes

**Síntoma**: Usuarios no pueden ver el reporte

**Solución**:
1. Ve a **Configuración** → **Usuarios y Compañías** → **Grupos**
2. Asegura que los usuarios tengan:
   - Grupo: "Usuario" (base.group_user)
   - O "Administrador de Inventario" para permisos completos

## 📚 Documentación Adicional

- **README.md**: Documentación general del módulo
- **INTEGRATION_GUIDE.md**: Guía detallada de integración
- **Comentarios en código**: Cada archivo tiene comentarios explicativos

## 🆘 Soporte

### Logs de Odoo

```bash
# Ver logs en tiempo real
tail -f /var/log/odoo/odoo-server.log

# Buscar errores específicos
grep -i "fill.rate" /var/log/odoo/odoo-server.log
```

### Shell de Odoo

```bash
# Acceder a shell de Odoo
odoo-bin shell -d tu_base_datos -c /path/to/odoo.conf
```

Probar funcionalidad:
```python
# En shell de Odoo
>>> FillRate = env['fill.rate.report']
>>> FillRate.generate_report_data()
>>> reports = FillRate.search([])
>>> print(f"Registros: {len(reports)}")
```

## ✨ Características Destacadas

✅ **100% Python** - Sin consultas SQL directas
✅ **Actualización automática** - Se actualiza al completar movimientos
✅ **Asistente de diagnóstico** - Detecta problemas automáticamente
✅ **Múltiples vistas** - Lista, Pivot, Gráficos
✅ **Indicadores visuales** - Colores según rendimiento
✅ **Filtros avanzados** - Por fecha, producto, rango de Fill Rate

## 🎉 ¡Listo!

Tu módulo Fill Rate está instalado y listo para usar.

**Próximos pasos:**
1. Ejecuta el Asistente de Diagnóstico
2. Ajusta configuración si es necesario
3. Genera datos del reporte
4. ¡Comienza a analizar tu Fill Rate!

---

**Versión**: 17.0.1.0.0 (Odoo 17)
**Licencia**: LGPL-3
