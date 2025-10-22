-- Script SQL para limpiar la vista antes de instalar/actualizar el módulo
-- Ejecutar este script directamente en la base de datos PostgreSQL si hay problemas de instalación

-- PASO 1: Eliminar la vista o tabla existente
DROP TABLE IF EXISTS pos_credit_note_detail CASCADE;
DROP VIEW IF EXISTS pos_credit_note_detail CASCADE;

-- PASO 2: Limpiar registros del modelo en Odoo (opcional pero recomendado)
DELETE FROM ir_model_data WHERE model = 'pos.credit.note.detail';
DELETE FROM ir_model_fields WHERE model = 'pos.credit.note.detail';
DELETE FROM ir_ui_view WHERE model = 'pos.credit.note.detail';

-- PASO 3: Verificar que se eliminó correctamente
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE tablename = 'pos_credit_note_detail';

-- Si aparece algún resultado, ejecutar de nuevo el DROP TABLE/VIEW
-- Si no aparece nada, el módulo se puede instalar/actualizar correctamente

-- NOTA: Después de ejecutar este script:
-- 1. Reinicia el servicio de Odoo
-- 2. Actualiza el módulo desde Aplicaciones
-- 3. Limpia la caché del navegador (Ctrl + Shift + R)
