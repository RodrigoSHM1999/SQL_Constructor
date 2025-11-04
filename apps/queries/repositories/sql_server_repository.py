"""
Repositorio para interactuar con SQL Server
"""
from django.db import connection
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)


class SQLServerRepository:
    """
    Maneja todas las interacciones directas con SQL Server.
    
    Proporciona métodos seguros para ejecutar consultas dinámicas.
    """
    
    def execute_query(self, sql, timeout=30):
        """
        Ejecuta una consulta SQL y retorna los resultados.
        
        Args:
            sql (str): Consulta SQL a ejecutar
            timeout (int): Timeout en segundos
        
        Returns:
            dict: {
                'success': bool,
                'data': list,
                'columns': list,
                'total_rows': int,
                'error': str
            }
        """
        result = {
            'success': False,
            'data': [],
            'columns': [],
            'total_rows': 0,
            'error': None
        }
        
        try:
            with connection.cursor() as cursor:
                # Establecer timeout
                cursor.execute(f"SET LOCK_TIMEOUT {timeout * 1000}")
                
                # Ejecutar consulta
                cursor.execute(sql)
                
                # Obtener nombres de columnas
                if cursor.description:
                    result['columns'] = [col[0] for col in cursor.description]
                    
                    # Obtener datos
                    result['data'] = cursor.fetchall()
                    result['total_rows'] = len(result['data'])
                
                result['success'] = True
                
        except Exception as e:
            logger.error(f"Error ejecutando SQL: {str(e)}\nSQL: {sql}")
            result['error'] = str(e)
        
        return result
    
    def execute_query_with_pagination(self, sql, page=1, page_size=50, timeout=30):
        """
        Ejecuta una consulta con paginación usando OFFSET/FETCH.
        
        Args:
            sql (str): Consulta SQL base
            page (int): Número de página (inicia en 1)
            page_size (int): Registros por página
            timeout (int): Timeout en segundos
        
        Returns:
            dict: {
                'success': bool,
                'data': list,
                'columns': list,
                'total_rows': int,
                'has_next': bool,
                'error': str
            }
        """
        result = {
            'success': False,
            'data': [],
            'columns': [],
            'total_rows': 0,
            'has_next': False,
            'error': None
        }
        
        try:
            # Calcular OFFSET
            offset = (page - 1) * page_size
            
            # Verificar si el SQL ya tiene ORDER BY
            sql_upper = sql.strip().upper()
            has_order_by = 'ORDER BY' in sql_upper
            
            # Si NO tiene ORDER BY, agregarlo (requerido por SQL Server para OFFSET)
            if not has_order_by:
                # Agregar ORDER BY al final del SQL original
                paginated_sql = f"{sql}\nORDER BY (SELECT NULL)"
            else:
                # Ya tiene ORDER BY, usar el SQL tal cual
                paginated_sql = sql
            
            # Agregar paginación al SQL (con o sin ORDER BY previo)
            paginated_sql = f"{paginated_sql}\nOFFSET {offset} ROWS\nFETCH NEXT {page_size + 1} ROWS ONLY"
            print("=" * 80)
            print("SQL GENERADO:")
            print(paginated_sql)
            print("=" * 80)
            with connection.cursor() as cursor:
                # Establecer timeout
                cursor.execute(f"SET LOCK_TIMEOUT {timeout * 1000}")
                
                # Ejecutar consulta paginada
                cursor.execute(paginated_sql)
                
                # Obtener nombres de columnas
                if cursor.description:
                    result['columns'] = [col[0] for col in cursor.description]
                    
                    # Obtener datos
                    rows = cursor.fetchall()
                    
                    # Verificar si hay más páginas
                    if len(rows) > page_size:
                        result['has_next'] = True
                        result['data'] = rows[:page_size]
                    else:
                        result['has_next'] = False
                        result['data'] = rows
                    
                    result['total_rows'] = len(result['data'])
                
                result['success'] = True
                
        except Exception as e:
            logger.error(f"Error ejecutando SQL paginado: {str(e)}")
            result['error'] = str(e)
        
        return result
    
    def get_table_schema(self, table_name):
        """
        Obtiene el esquema de una tabla.
        
        Args:
            table_name (str): Nombre de la tabla (puede incluir esquema)
        
        Returns:
            dict: {
                'success': bool,
                'columns': list,
                'error': str
            }
        """
        result = {
            'success': False,
            'columns': [],
            'error': None
        }
        
        try:
            # Separar esquema y tabla si viene junto
            parts = table_name.split('.')
            if len(parts) == 2:
                schema, table = parts
            else:
                schema = 'dbo'
                table = table_name
            
            sql = """
            SELECT 
                COLUMN_NAME as name,
                DATA_TYPE as type,
                CHARACTER_MAXIMUM_LENGTH as max_length,
                IS_NULLABLE as nullable
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
            """
            
            with connection.cursor() as cursor:
                cursor.execute(sql, [schema, table])
                columns = cursor.fetchall()
                
                result['columns'] = [
                    {
                        'name': col[0],
                        'type': col[1],
                        'max_length': col[2],
                        'nullable': col[3] == 'YES'
                    }
                    for col in columns
                ]
                
                result['success'] = True
                
        except Exception as e:
            logger.error(f"Error obteniendo esquema de tabla {table_name}: {str(e)}")
            result['error'] = str(e)
        
        return result
    
    def validate_table_exists(self, table_name):
        """
        Valida si una tabla existe en la base de datos.
        
        Args:
            table_name (str): Nombre de la tabla
        
        Returns:
            bool: True si existe
        """
        try:
            parts = table_name.split('.')
            if len(parts) == 2:
                schema, table = parts
            else:
                schema = 'dbo'
                table = table_name
            
            sql = """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
            """
            
            with connection.cursor() as cursor:
                cursor.execute(sql, [schema, table])
                count = cursor.fetchone()[0]
                return count > 0
                
        except Exception as e:
            logger.error(f"Error validando existencia de tabla {table_name}: {str(e)}")
            return False
    
    def get_database_info(self):
        """
        Obtiene información de la base de datos conectada.
        
        Returns:
            dict: Información de la BD
        """
        result = {
            'success': False,
            'info': {},
            'error': None
        }
        
        try:
            with connection.cursor() as cursor:
                # Versión de SQL Server
                cursor.execute("SELECT @@VERSION")
                version = cursor.fetchone()[0]
                
                # Nombre de la BD
                cursor.execute("SELECT DB_NAME()")
                db_name = cursor.fetchone()[0]
                
                result['info'] = {
                    'version': version,
                    'database': db_name
                }
                result['success'] = True
                
        except Exception as e:
            logger.error(f"Error obteniendo info de BD: {str(e)}")
            result['error'] = str(e)
        
        return result