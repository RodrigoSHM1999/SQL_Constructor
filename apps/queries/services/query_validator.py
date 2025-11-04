"""
Servicio para validar seguridad y sintaxis de consultas SQL
"""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import re


class QueryValidatorService:
    """
    Valida que las consultas SQL sean seguras y correctas.
    
    Previene inyección SQL y comandos peligrosos.
    """
    
    # Comandos SQL peligrosos que no se permiten
    DANGEROUS_COMMANDS = [
        'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 
        'TRUNCATE', 'EXEC', 'EXECUTE', 'CREATE', 'GRANT',
        'REVOKE', 'DENY', 'BACKUP', 'RESTORE', 'SHUTDOWN'
    ]
    
    # Palabras clave SQL permitidas en FROM
    ALLOWED_JOIN_KEYWORDS = [
        'INNER', 'LEFT', 'RIGHT', 'FULL', 'CROSS', 
        'JOIN', 'ON', 'AS', 'FROM'
    ]
    
    @staticmethod
    def validate_sql_safety(sql_text):
        """
        Valida que el texto SQL no contenga comandos peligrosos.
        
        Args:
            sql_text (str): Texto SQL a validar
            
        Raises:
            ValidationError: Si se encuentra un comando peligroso
            
        Returns:
            bool: True si es seguro
        """
        if not sql_text:
            return True
        
        sql_upper = sql_text.upper()
        
        for command in QueryValidatorService.DANGEROUS_COMMANDS:
            # Buscar el comando como palabra completa (no parte de otra palabra)
            pattern = r'\b' + command + r'\b'
            if re.search(pattern, sql_upper):
                raise ValidationError(
                    _(f'Comando peligroso detectado: {command}. No se permite este comando por seguridad.')
                )
        
        return True
    
    @staticmethod
    def validate_select_clause(select_clause):
        """
        Valida la cláusula SELECT.
        
        Args:
            select_clause (str): Cláusula SELECT
            
        Raises:
            ValidationError: Si la cláusula es inválida
            
        Returns:
            bool: True si es válida
        """
        if not select_clause or not select_clause.strip():
            raise ValidationError(_('La cláusula SELECT no puede estar vacía'))
        
        # Validar seguridad
        QueryValidatorService.validate_sql_safety(select_clause)
        
        # Verificar que no contenga palabras clave peligrosas en lugares incorrectos
        select_upper = select_clause.upper()
        if 'FROM' in select_upper or 'WHERE' in select_upper:
            raise ValidationError(
                _('La cláusula SELECT no debe contener FROM o WHERE. Estos van en sus respectivos campos.')
            )
        
        return True
    
    @staticmethod
    def validate_from_clause(from_clause):
        """
        Valida la cláusula FROM con JOINS.
        
        Args:
            from_clause (str): Cláusula FROM completa con JOINS
            
        Raises:
            ValidationError: Si la cláusula es inválida
            
        Returns:
            bool: True si es válida
        """
        if not from_clause or not from_clause.strip():
            raise ValidationError(_('La cláusula FROM no puede estar vacía'))
        
        # Validar seguridad
        QueryValidatorService.validate_sql_safety(from_clause)
        
        # Verificar que empiece con FROM
        from_upper = from_clause.strip().upper()
        if not from_upper.startswith('FROM'):
            raise ValidationError(
                _('La cláusula debe comenzar con FROM')
            )
        
        # Validar que los JOINS tengan la estructura correcta
        if 'JOIN' in from_upper:
            # Verificar que cada JOIN tenga un ON
            joins = re.findall(r'(INNER|LEFT|RIGHT|FULL|CROSS)?\s*JOIN', from_upper)
            ons = re.findall(r'\bON\b', from_upper)
            
            # CROSS JOIN no requiere ON, los demás sí
            cross_joins = from_upper.count('CROSS JOIN')
            required_ons = len(joins) - cross_joins
            
            if len(ons) < required_ons:
                raise ValidationError(
                    _(f'Faltan cláusulas ON. Se encontraron {len(joins)} JOINs pero solo {len(ons)} ON')
                )
        
        return True
    
    @staticmethod
    def validate_where_clause(where_clause):
        """
        Valida la cláusula WHERE con parámetros.
        
        Args:
            where_clause (str): Cláusula WHERE con %1, %2, etc.
            
        Raises:
            ValidationError: Si la cláusula es inválida
            
        Returns:
            bool: True si es válida
        """
        if not where_clause or not where_clause.strip():
            return True  # WHERE es opcional
        
        # Validar seguridad
        QueryValidatorService.validate_sql_safety(where_clause)
        
        # Extraer posiciones de parámetros (%1, %2, etc.)
        parametros = re.findall(r'%(\d+)', where_clause)
        
        if not parametros:
            # WHERE sin parámetros es válido pero poco común
            pass
        else:
            # Verificar que los parámetros sean consecutivos desde 1
            parametros_unicos = sorted(set(int(p) for p in parametros))
            if parametros_unicos[0] != 1:
                raise ValidationError(
                    _('Los parámetros deben comenzar desde %1')
                )
            
            # Verificar secuencia (advertencia, no error)
            for i, param in enumerate(parametros_unicos, start=1):
                if param != i:
                    # Solo advertencia, no bloquear
                    pass
        
        return True
    
    @staticmethod
    def extract_parameter_positions(where_clause):
        """
        Extrae todas las posiciones de parámetros del WHERE.
        
        Args:
            where_clause (str): Cláusula WHERE
            
        Returns:
            list: Lista de posiciones únicas ordenadas [1, 2, 3, ...]
        """
        if not where_clause:
            return []
        
        parametros = re.findall(r'%(\d+)', where_clause)
        return sorted(set(int(p) for p in parametros))
    
    @staticmethod
    def validate_table_name(table_name):
        """
        Valida que el nombre de tabla sea seguro.
        
        Args:
            table_name (str): Nombre de tabla (puede incluir esquema)
            
        Raises:
            ValidationError: Si el nombre es inválido
            
        Returns:
            bool: True si es válido
        """
        if not table_name or not table_name.strip():
            raise ValidationError(_('El nombre de tabla no puede estar vacío'))
        
        # Permitir: esquema.tabla o solo tabla
        # Caracteres permitidos: letras, números, punto, guión bajo
        pattern = r'^[a-zA-Z_][\w]*(\.[a-zA-Z_][\w]*)?$'
        
        if not re.match(pattern, table_name.strip()):
            raise ValidationError(
                _(f'Nombre de tabla inválido: {table_name}. Use formato: esquema.tabla o tabla')
            )
        
        return True
    
    @staticmethod
    def check_sql_injection_patterns(text):
        """
        Busca patrones comunes de inyección SQL.
        
        Args:
            text (str): Texto a analizar
            
        Raises:
            ValidationError: Si se detecta un patrón sospechoso
            
        Returns:
            bool: True si no se detectan patrones
        """
        if not text:
            return True
        
        # Patrones sospechosos
        suspicious_patterns = [
            r"';",  # Comilla simple seguida de punto y coma
            r'--',  # Comentarios SQL
            r'/\*',  # Comentarios multilínea
            r'\*/',
            r'@@',  # Variables del sistema
            r'xp_',  # Procedimientos extendidos peligrosos
            r'sp_',  # Procedimientos del sistema
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                raise ValidationError(
                    _(f'Patrón sospechoso detectado: {pattern}. Por seguridad, no se permite.')
                )
        
        return True
    
    @staticmethod
    def validate_full_query(select_clause, from_clause, where_clause):
        """
        Valida la consulta completa.
        
        Args:
            select_clause (str): Cláusula SELECT
            from_clause (str): Cláusula FROM
            where_clause (str): Cláusula WHERE
            
        Raises:
            ValidationError: Si alguna parte es inválida
            
        Returns:
            dict: Resultado de validación con detalles
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'parameter_positions': []
        }
        
        try:
            QueryValidatorService.validate_select_clause(select_clause)
        except ValidationError as e:
            result['valid'] = False
            result['errors'].append(f"SELECT: {str(e)}")
        
        try:
            QueryValidatorService.validate_from_clause(from_clause)
        except ValidationError as e:
            result['valid'] = False
            result['errors'].append(f"FROM: {str(e)}")
        
        try:
            QueryValidatorService.validate_where_clause(where_clause)
            result['parameter_positions'] = QueryValidatorService.extract_parameter_positions(where_clause)
        except ValidationError as e:
            result['valid'] = False
            result['errors'].append(f"WHERE: {str(e)}")
        
        # Validar query completa
        full_query = f"{select_clause} {from_clause} {where_clause}"
        try:
            QueryValidatorService.check_sql_injection_patterns(full_query)
        except ValidationError as e:
            result['valid'] = False
            result['errors'].append(str(e))
        
        return result