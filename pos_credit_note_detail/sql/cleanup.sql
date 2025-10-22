-- Script SQL para limpiar la vista antes de instalar el módulo
-- Ejecutar este script directamente en la base de datos PostgreSQL si hay problemas de instalación

-- Eliminar la vista o tabla existente
DROP TABLE IF EXISTS pos_credit_note_detail CASCADE;
DROP VIEW IF EXISTS pos_credit_note_detail CASCADE;

-- Verificar que se eliminó correctamente
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE tablename = 'pos_credit_note_detail';

-- Si aparece algún resultado, ejecutar de nuevo el DROP TABLE/VIEW
-- Si no aparece nada, el módulo se puede instalar correctamente
