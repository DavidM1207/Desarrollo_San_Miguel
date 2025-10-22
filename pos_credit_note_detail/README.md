# Módulo: Detalle de Notas de Crédito POS

## Descripción
Este módulo permite visualizar el detalle individual de las notas de crédito del Punto de Venta (POS) que se agrupan por sesión en el libro mayor de Odoo 17.

## Problema que resuelve
En Odoo 17, cuando se generan múltiples notas de crédito en una sesión de POS, el libro mayor y los apuntes contables muestran un solo registro agrupado para todas las notas de crédito de esa sesión en la cuenta "211040020000 Notas de Crédito por Aplicar". Esto dificulta ver el detalle individual de cada nota de crédito y realizar conciliaciones específicas.

## Características

### Vista de Lista con las siguientes columnas:
- **Fecha**: Fecha del apunte contable
- **Diario**: Diario contable utilizado
- **Nota de Crédito**: Número de la nota de crédito
- **Etiqueta**: Descripción del apunte contable
- **Débito**: Monto en débito
- **Crédito**: Monto en crédito
- **Balance**: Balance del apunte
- **Emparejamiento**: Estado de conciliación
- **Distribución Analítica**: Distribución de cuentas analíticas

### Funcionalidades adicionales:
1. **Filtros inteligentes**:
   - Por fecha (Hoy, Este Mes, Mes Anterior)
   - Con débito/crédito
   - Conciliadas/No conciliadas
   - Con distribución analítica

2. **Agrupaciones**:
   - Por fecha
   - Por diario
   - Por empresa/partner
   - Por sesión de POS
   - Por emparejamiento

3. **Acciones rápidas**:
   - Ver asiento contable completo
   - Ver orden de POS relacionada
   - Abrir asistente de conciliación

4. **Totales automáticos**:
   - Total de débitos
   - Total de créditos
   - Balance total

## Instalación

### IMPORTANTE: Limpiar instalaciones previas

Si ya intentaste instalar el módulo anteriormente y obtuviste un error, primero debes limpiar la base de datos:

```bash
# Conectarse a PostgreSQL
psql -U odoo -d tu_base_de_datos

# Ejecutar estos comandos
DROP TABLE IF EXISTS pos_credit_note_detail CASCADE;
DROP VIEW IF EXISTS pos_credit_note_detail CASCADE;

# Salir
\q
```

Alternativamente, puedes usar el script de limpieza incluido:
```bash
psql -U odoo -d tu_base_de_datos -f /ruta/al/modulo/sql/cleanup.sql
```

### Paso 1: Copiar el módulo
Copia la carpeta `pos_credit_note_detail` en el directorio de addons de tu instalación de Odoo.

```bash
cp -r pos_credit_note_detail /ruta/a/odoo/addons/
```

### Paso 2: Actualizar lista de aplicaciones
1. Inicia sesión en Odoo como administrador
2. Activa el modo desarrollador (Configuración → Activar modo de desarrollador)
3. Ve a Aplicaciones
4. Haz clic en "Actualizar lista de aplicaciones"
5. Busca "Detalle de Notas de Crédito POS"
6. Haz clic en "Instalar"

## Uso

### Acceder a la vista
Una vez instalado el módulo, puedes acceder a la vista de dos formas:

1. **Desde Contabilidad**:
   - Contabilidad → Clientes → Detalle NC POS

2. **Desde Punto de Venta**:
   - Punto de Venta → Detalle de Notas de Crédito

### Ver el detalle
La vista mostrará automáticamente todas las líneas de apuntes contables de la cuenta "211040020000 Notas de Crédito por Aplicar", desglosadas individualmente.

### Filtrar información
Utiliza los filtros predefinidos o crea filtros personalizados:
- Busca por fecha, número de nota, diario o empresa
- Aplica filtros de "Este Mes" o "No Conciliadas"
- Agrupa por sesión de POS para ver qué notas pertenecen a cada sesión

### Conciliar
1. Selecciona una línea no conciliada
2. Haz clic en "Abrir"
3. En el formulario, haz clic en "Conciliar"
4. Sigue el proceso de conciliación estándar de Odoo

## Requisitos técnicos
- Odoo 17.0 o superior
- Módulos dependientes:
  - `account` (Contabilidad)
  - `point_of_sale` (Punto de Venta)

## Notas importantes

### Cuenta específica
El módulo está configurado para mostrar únicamente los registros de la cuenta con código **211040020000**. Si tu cuenta tiene un código diferente, debes modificar la vista SQL en el archivo `models/__init__.py`:

```python
WHERE 
    aa.code = '211040020000'  # Cambia este código por el tuyo
```

### Permisos
El módulo respeta los permisos de contabilidad de Odoo:
- Los usuarios con rol "Contabilidad/Usuario" pueden ver los registros
- Los gerentes de contabilidad tienen acceso completo

### Vista de solo lectura
Esta es una vista de solo lectura. Los registros no se pueden crear, editar o eliminar desde esta vista. Todos los cambios deben realizarse a través de los asientos contables originales.

## Soporte técnico
Para personalizar el módulo según tus necesidades específicas, consulta con tu equipo de desarrollo o un partner certificado de Odoo.

## Solución de problemas

### Error: "pos_credit_note_detail" is not a view

Este es el error más común durante la instalación. Ocurre cuando ya existe una tabla o vista con ese nombre en la base de datos.

**Solución rápida:**
```bash
psql -U odoo -d tu_base_de_datos -c "DROP TABLE IF EXISTS pos_credit_note_detail CASCADE; DROP VIEW IF EXISTS pos_credit_note_detail CASCADE;"
```

Para más detalles, consulta el archivo [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## Licencia
LGPL-3

## Autor
Desarrollado para facilitar la gestión de notas de crédito del POS en Odoo 17.
