"""
Servicio para construir consultas SQL dinámicas
"""
from django.utils.translation import gettext_lazy as _
from .query_validator import QueryValidatorService
import re


class QueryBuilderService:
    """
    Construye consultas SQL dinámicas reemplazando parámetros
    según los valores proporcionados por el usuario.
    """
    
    @staticmethod
    def build_query(query_obj, params_dict=None):
        """
        Construye la consulta SQL completa con parámetros opcionales.
        
        Args:
            query_obj: Instancia de DynamicQuery
            params_dict: Dict con valores {posicion_where: valor}
                        Ej: {1: 'Activo', 2: 100}
                        Si es None o vacío, retorna consulta sin WHERE
        
        Returns:
            str: SQL final ejecutable
        """
        select_clause = query_obj.select_clause.strip()
        from_clause = query_obj.from_clause.strip()
        where_clause = query_obj.where_clause.strip()
        
        # Separar WHERE de GROUP BY y ORDER BY si están mezclados
        where_part, group_by_part, order_by_part = QueryBuilderService._separate_clauses(where_clause)
        
        # Construir SELECT y FROM
        sql_parts = [
            f"SELECT {select_clause}",
            from_clause
        ]
        
        # Construir WHERE solo si hay parámetros
        if where_part and params_dict:
            where_conditions = QueryBuilderService._build_where_conditions(
                query_obj, 
                params_dict,
                where_part
            )
            if where_conditions:
                sql_parts.append(f"WHERE {where_conditions}")
        
        # Agregar GROUP BY si existe
        if group_by_part:
            sql_parts.append(group_by_part)
        
        # Agregar ORDER BY si existe
        if order_by_part:
            sql_parts.append(order_by_part)
        
        return "\n".join(sql_parts)
    
    @staticmethod
    def _separate_clauses(where_clause):
        """
        Separa WHERE, GROUP BY y ORDER BY de una cláusula mixta correctamente,
        incluso cuando vienen en líneas diferentes.
        """
        if not where_clause:
            return "", "", ""

        text = where_clause.strip()

        # Normalizar espacios y saltos de línea
        text = re.sub(r'\s+', ' ', text)

        # Patrón robusto: detecta posiciones de GROUP BY y ORDER BY
        group_by_match = re.search(r'\bGROUP BY\b', text, re.IGNORECASE)
        order_by_match = re.search(r'\bORDER BY\b', text, re.IGNORECASE)

        where_part = text
        group_by_part = ""
        order_by_part = ""

        if group_by_match:
            where_part = text[:group_by_match.start()].strip()
            if order_by_match and order_by_match.start() > group_by_match.start():
                group_by_part = text[group_by_match.start():order_by_match.start()].strip()
                order_by_part = text[order_by_match.start():].strip()
            else:
                group_by_part = text[group_by_match.start():].strip()
        elif order_by_match:
            where_part = text[:order_by_match.start()].strip()
            order_by_part = text[order_by_match.start():].strip()

        return where_part, group_by_part, order_by_part

    
    @staticmethod
    def _build_where_conditions(query_obj, params_dict, where_template):
        """
        Construye las condiciones WHERE solo con parámetros proporcionados.
        
        Si un parámetro no está en params_dict, su condición se omite.
        
        Args:
            query_obj: Instancia de DynamicQuery
            params_dict: Dict {posicion_where: valor}
            where_template: Template de WHERE (sin GROUP BY ni ORDER BY)
        
        Returns:
            str: Condiciones WHERE construidas
        """
        if not where_template:
            return ""
        
        # Obtener parámetros configurados
        parametros = {
            p.posicion_where: p 
            for p in query_obj.parametros.all()
        }
        
        # Separar condiciones por AND
        conditions = QueryBuilderService._parse_conditions(where_template)
        
        active_conditions = []
        
        for condition in conditions:
            # Extraer posiciones de parámetros en esta condición (%1, %2, etc.)
            param_positions = QueryBuilderService._extract_param_positions(condition)
            
            # Solo incluir si TODOS los parámetros necesarios están presentes
            if all(pos in params_dict and params_dict[pos] not in [None, ''] 
                   for pos in param_positions):
                
                # Reemplazar %N con valores formateados
                replaced = condition
                for pos in param_positions:
                    param = parametros.get(pos)
                    if param:
                        value = param.format_value(params_dict[pos])
                        if value is not None:
                            replaced = replaced.replace(f"%{pos}", value)
                
                active_conditions.append(replaced)
        
        return " AND ".join(active_conditions) if active_conditions else ""
    
    @staticmethod
    def _parse_conditions(where_clause):
        """
        Separa las condiciones WHERE por AND.
        
        TODO: Mejorar para soportar OR y paréntesis complejos
        
        Args:
            where_clause (str): Cláusula WHERE
        
        Returns:
            list: Lista de condiciones individuales
        """
        # Split simple por AND (case insensitive)
        # Nota: Esto no maneja correctamente OR ni paréntesis anidados
        conditions = re.split(r'\s+AND\s+', where_clause, flags=re.IGNORECASE)
        return [c.strip() for c in conditions if c.strip()]
    
    @staticmethod
    def _extract_param_positions(condition):
        """
        Extrae las posiciones de parámetros (%1, %2, etc.) de una condición.
        
        Args:
            condition (str): Condición SQL
        
        Returns:
            list: Lista de posiciones (números enteros)
        """
        matches = re.findall(r'%(\d+)', condition)
        return [int(m) for m in matches]
    
    @staticmethod
    def get_required_parameters(query_obj):
        """
        Retorna los parámetros requeridos para una consulta.
        
        Args:
            query_obj: Instancia de DynamicQuery
        
        Returns:
            list: Lista de QueryParameter que son requeridos
        """
        return query_obj.parametros.filter(requerido=True).order_by('orden')
    
    @staticmethod
    def get_visible_parameters(query_obj):
        """
        Retorna los parámetros visibles para el usuario final.
        
        Args:
            query_obj: Instancia de DynamicQuery
        
        Returns:
            QuerySet: Parámetros visibles ordenados
        """
        return query_obj.parametros.filter(visible=True).order_by('orden')
    
    @staticmethod
    def validate_parameters(query_obj, params_dict):
        """
        Valida que los parámetros requeridos estén presentes y sean válidos.
        
        Args:
            query_obj: Instancia de DynamicQuery
            params_dict: Dict con valores {posicion_where: valor}
        
        Returns:
            dict: {'valid': bool, 'errors': list}
        """
        result = {
            'valid': True,
            'errors': []
        }
        
        required_params = QueryBuilderService.get_required_parameters(query_obj)
        
        for param in required_params:
            if param.posicion_where not in params_dict:
                result['valid'] = False
                result['errors'].append(
                    f"El parámetro '{param.etiqueta_usuario}' es obligatorio"
                )
            elif params_dict[param.posicion_where] in [None, '']:
                result['valid'] = False
                result['errors'].append(
                    f"El parámetro '{param.etiqueta_usuario}' no puede estar vacío"
                )
        
        return result
    
    @staticmethod
    def build_test_query(query_obj, test_values=None):
        """
        Construye una consulta de prueba con valores simulados.
        
        Args:
            query_obj: Instancia de DynamicQuery
            test_values: Dict opcional con valores de prueba
        
        Returns:
            str: SQL de prueba
        """
        if test_values is None:
            # Generar valores de prueba automáticos
            test_values = {}
            for param in query_obj.parametros.all():
                if param.valor_por_defecto:
                    test_values[param.posicion_where] = param.valor_por_defecto
                else:
                    # Valores de prueba según tipo
                    test_values[param.posicion_where] = QueryBuilderService._get_test_value(param.tipo_dato)
        
        return QueryBuilderService.build_query(query_obj, test_values)
    
    @staticmethod
    def _get_test_value(tipo_dato):
        """
        Genera un valor de prueba según el tipo de dato.
        
        Args:
            tipo_dato (str): Tipo de dato del parámetro
        
        Returns:
            str: Valor de prueba
        """
        test_values = {
            'texto': 'TEST',
            'numero': '1',
            'decimal': '1.0',
            'fecha': '2025-01-01',
            'boolean': 'true'
        }
        return test_values.get(tipo_dato, 'TEST')