"""
Servicio para parsear y analizar la cláusula FROM con JOINS
"""
import re
from django.utils.translation import gettext_lazy as _


class FromParserService:
    """
    Parsea la cláusula FROM para extraer información sobre
    tablas base, JOINS, alias y condiciones.
    """
    
    @staticmethod
    def parse_from_clause(from_clause):
        """
        Parsea la cláusula FROM y retorna información estructurada.
        
        Args:
            from_clause (str): Cláusula FROM completa
            
        Returns:
            dict: Información estructurada sobre la cláusula
        """
        if not from_clause:
            return {
                'base_table': None,
                'base_alias': None,
                'joins': [],
                'all_tables': [],
                'preview': []
            }
        
        result = {
            'base_table': None,
            'base_alias': None,
            'joins': [],
            'all_tables': [],
            'preview': []
        }
        
        # Limpiar y normalizar
        from_clause = from_clause.strip()
        
        # Extraer tabla base
        base_info = FromParserService._extract_base_table(from_clause)
        result['base_table'] = base_info['table']
        result['base_alias'] = base_info['alias']
        result['all_tables'].append(base_info['table'])
        
        # Agregar a preview
        result['preview'].append({
            'type': 'BASE',
            'icon': '📦',
            'table': base_info['table'],
            'alias': base_info['alias'],
            'condition': None
        })
        
        # Extraer JOINS
        joins = FromParserService._extract_joins(from_clause)
        result['joins'] = joins
        
        for join in joins:
            result['all_tables'].append(join['table'])
            result['preview'].append({
                'type': join['type'],
                'icon': FromParserService._get_join_icon(join['type']),
                'table': join['table'],
                'alias': join['alias'],
                'condition': join['condition']
            })
        
        return result
    
    @staticmethod
    def _extract_base_table(from_clause):
        """
        Extrae la tabla base del FROM.
        
        Args:
            from_clause (str): Cláusula FROM
            
        Returns:
            dict: {'table': nombre, 'alias': alias o None}
        """
        # Patrón: FROM tabla [AS] alias
        # Capturar hasta el primer JOIN o fin de línea
        pattern = r'FROM\s+([a-zA-Z_][\w.]*)\s*(?:AS\s+)?([a-zA-Z_][\w]*)?'
        match = re.search(pattern, from_clause, re.IGNORECASE)
        
        if match:
            return {
                'table': match.group(1),
                'alias': match.group(2) if match.group(2) else None
            }
        
        return {'table': None, 'alias': None}
    
    @staticmethod
    def _extract_joins(from_clause):
        """
        Extrae todos los JOINS de la cláusula FROM.
        
        Args:
            from_clause (str): Cláusula FROM
            
        Returns:
            list: Lista de diccionarios con información de cada JOIN
        """
        joins = []
        
        # Patrón mejorado para capturar JOINS
        # Captura: (TIPO) JOIN tabla [AS] alias ON condicion (hasta el próximo JOIN o fin)
        pattern = r'(INNER|LEFT|RIGHT|FULL|CROSS)?\s*JOIN\s+([a-zA-Z_][\w.]*)\s*(?:AS\s+)?([a-zA-Z_][\w]*)?\s*(?:ON\s+((?:(?!JOIN).)+))?'
        
        matches = re.finditer(pattern, from_clause, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            join_type = match.group(1) if match.group(1) else 'INNER'
            table = match.group(2)
            alias = match.group(3) if match.group(3) else None
            condition = match.group(4).strip() if match.group(4) else None
            
            joins.append({
                'type': join_type.upper(),
                'table': table,
                'alias': alias,
                'condition': condition
            })
        
        return joins
        
    @staticmethod
    def _get_join_icon(join_type):
        """
        Retorna un ícono según el tipo de JOIN.
        
        Args:
            join_type (str): Tipo de JOIN
            
        Returns:
            str: Emoji representativo
        """
        icons = {
            'INNER': '🔗',
            'LEFT': '◀️',
            'RIGHT': '▶️',
            'FULL': '↔️',
            'CROSS': '✖️'
        }
        return icons.get(join_type.upper(), '🔗')
    
    @staticmethod
    def get_preview_html(from_clause):
        """
        Genera HTML de vista previa estructurada del FROM.
        
        Args:
            from_clause (str): Cláusula FROM
            
        Returns:
            str: HTML formateado
        """
        parsed = FromParserService.parse_from_clause(from_clause)
        
        if not parsed['base_table']:
            return '<p class="text-gray-500">No se pudo parsear la cláusula FROM</p>'
        
        html_parts = ['<div class="space-y-2">']
        
        for item in parsed['preview']:
            alias_text = f' <span class="text-blue-600">AS {item["alias"]}</span>' if item['alias'] else ''
            condition_text = f'<div class="text-sm text-gray-600 ml-8">ON {item["condition"]}</div>' if item['condition'] else ''
            
            html_parts.append(f'''
                <div class="border-l-4 border-blue-500 pl-4 py-2">
                    <div class="font-mono text-sm">
                        {item['icon']} <span class="font-bold">{item['type']}</span>: 
                        <span class="text-green-600">{item['table']}</span>{alias_text}
                    </div>
                    {condition_text}
                </div>
            ''')
        
        html_parts.append('</div>')
        
        return ''.join(html_parts)
    
    @staticmethod
    def get_all_aliases(from_clause):
        """
        Extrae todos los alias definidos en el FROM.
        
        Args:
            from_clause (str): Cláusula FROM
            
        Returns:
            dict: {alias: tabla}
        """
        parsed = FromParserService.parse_from_clause(from_clause)
        aliases = {}
        
        if parsed['base_alias']:
            aliases[parsed['base_alias']] = parsed['base_table']
        
        for join in parsed['joins']:
            if join['alias']:
                aliases[join['alias']] = join['table']
        
        return aliases
    
    @staticmethod
    def validate_aliases_in_select(select_clause, from_clause):
        """
        Valida que los alias usados en SELECT estén definidos en FROM.
        
        Args:
            select_clause (str): Cláusula SELECT
            from_clause (str): Cláusula FROM
            
        Returns:
            dict: {'valid': bool, 'undefined_aliases': list}
        """
        # Extraer alias del FROM
        defined_aliases = FromParserService.get_all_aliases(from_clause)
        
        # Extraer alias usados en SELECT (patrón: alias.campo)
        used_aliases = re.findall(r'\b([a-zA-Z_][\w]*)\.\w+', select_clause)
        used_aliases = set(used_aliases)
        
        # Encontrar alias no definidos
        undefined = [alias for alias in used_aliases if alias not in defined_aliases]
        
        return {
            'valid': len(undefined) == 0,
            'undefined_aliases': undefined,
            'defined_aliases': list(defined_aliases.keys())
        }