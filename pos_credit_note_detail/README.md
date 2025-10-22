# Detalle de Notas de Crédito POS - Versión 2.0

## 🎯 Enfoque Correcto

Este módulo **NO crea una vista SQL estática**. En su lugar, utiliza el modelo `account.move.line` nativo de Odoo con un filtro de dominio, funcionando exactamente como "Apuntes Contables" pero mostrando solo las notas de crédito del POS.

## ✅ Ventajas de este enfoque

1. **Actualización en tiempo real** - Los cambios se reflejan inmediatamente
2. **Conciliación nativa** - Funciona exactamente como apuntes contables
3. **Agrupación por sesión POS** - Funciona correctamente
4. **Todas las funciones estándar** - Filtros, búsquedas, exportación, etc.
5. **Sin campos adicionales problemáticos** - Usa los campos nativos de Odoo

## 📋 ¿Qué hace el módulo?

- Agrega un campo `pos_session_id` a `account.move.line` (relacionado con `move_id.pos_session_id`)
- Crea una acción de ventana que muestra apuntes contables con dominio:
  ```python
  [('account_id.code', '=', '211040020000'), ('parent_state', '=', 'posted')]
  ```
- Agrega un filtro de agrupación por "Sesión POS"
- Muestra el menú solo en Punto de Venta

## 🚀 Instalación

### Requisitos
- Odoo 17.0
- Módulos: `account`, `point_of_sale`

### Pasos

1. **Copiar el módulo**
   ```bash
   cp -r pos_credit_note_detail_v2 /ruta/a/odoo/addons/
   ```

2. **Reiniciar Odoo**
   ```bash
   sudo service odoo restart
   ```

3. **Instalar desde la interfaz**
   - Aplicaciones → Actualizar lista de aplicaciones
   - Buscar: "Detalle NC POS"
   - Instalar

## 📍 Uso

### Acceder a la vista
**Punto de Venta → Detalle de Notas de Crédito**

### Funciones disponibles

1. **Ver registros en tiempo real**
   - Crea una nota de crédito en POS
   - Actualiza la vista (F5)
   - Aparecerá inmediatamente

2. **Conciliar**
   - Selecciona uno o más registros
   - Acción → Conciliar
   - Funciona exactamente como apuntes contables

3. **Agrupar por sesión**
   - Clic en "Agrupar por"
   - Seleccionar "Sesión POS"
   - Verás los registros agrupados por sesión

4. **Todas las funciones estándar**
   - Filtros por fecha, cuenta, empresa
   - Exportar a Excel
   - Vistas: Lista, Formulario, Pivot, Gráfico
   - Búsqueda avanzada

## ⚙️ Configuración

### Cambiar el código de cuenta

Si tu cuenta de notas de crédito tiene un código diferente a `211040020000`:

1. Editar `views/pos_credit_note_views.xml`
2. Buscar la línea:
   ```xml
   <field name="domain">[('account_id.code', '=', '211040020000'), ...]</field>
   ```
3. Cambiar `211040020000` por tu código de cuenta
4. Actualizar el módulo

### Agregar más filtros

Puedes agregar filtros adicionales editando la vista de búsqueda en el archivo XML.

## 🔧 Estructura del módulo

```
pos_credit_note_detail_v2/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── pos_credit_note_detail.py  (Hereda account.move.line)
├── views/
│   └── pos_credit_note_views.xml  (Acción con dominio filtrado)
└── README.md
```

## 🆚 Diferencias con la versión anterior

| Aspecto | Versión 1.0 (❌ Incorrecta) | Versión 2.0 (✅ Correcta) |
|---------|---------------------------|-------------------------|
| Tipo | Vista SQL estática | Modelo nativo con filtro |
| Actualización | Manual/No automática | Tiempo real |
| Conciliación | No funcionaba | Funciona perfectamente |
| Agrupación POS | No funcionaba (NULL) | Funciona correctamente |
| Campos | Muchos campos extras | Solo campos nativos |
| Complejidad | Alta | Baja |

## 💡 Por qué este enfoque es mejor

### Problema de la Vista SQL:
```sql
CREATE VIEW pos_credit_note_detail AS (
    SELECT ...
)
```
- Los datos quedan "congelados" al momento de la consulta
- No se actualizan automáticamente
- La conciliación no funciona (opera sobre una vista, no sobre registros reales)
- Los campos relacionados no funcionan correctamente

### Solución con Dominio:
```python
domain = [('account_id.code', '=', '211040020000')]
```
- Opera directamente sobre `account.move.line`
- Se actualiza en tiempo real
- Todas las funciones nativas funcionan
- Aprovecha toda la lógica de negocio de Odoo

## 📞 Notas importantes

- **Sin limpieza de BD necesaria**: Este módulo no crea tablas ni vistas SQL
- **Compatible**: Funciona con cualquier instalación de Odoo 17
- **Mantenible**: Si Odoo actualiza `account.move.line`, funciona automáticamente
- **Ubicación del menú**: Solo en Punto de Venta (no en Contabilidad)

## 🐛 Solución de problemas

### No aparecen registros
- Verifica que existan registros en la cuenta `211040020000`
- Verifica que los asientos estén publicados (`parent_state = 'posted'`)
- Verifica el código de cuenta en el dominio

### La agrupación por sesión no funciona
- Asegúrate de que el módulo esté correctamente instalado
- Verifica que los asientos tengan `pos_session_id` en el move

### No puedo conciliar
- La conciliación funciona exactamente igual que en apuntes contables
- Solo se pueden conciliar registros de cuentas conciliables

## 📄 Licencia

LGPL-3

## 👨‍💻 Desarrollo

Este módulo utiliza el enfoque recomendado por Odoo para crear vistas filtradas de modelos existentes, en lugar de duplicar datos o crear estructuras complejas.
