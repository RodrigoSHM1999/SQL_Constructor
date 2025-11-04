"""
Modelo para consultas SQL dinámicas
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class DynamicQuery(models.Model):
    """
    Representa una consulta SQL dinámica creada por técnicos.
    
    Esta consulta puede tener parámetros configurables que el usuario
    final llenará al momento de ejecutarla.
    """
    
    nombre = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=_("Nombre de la consulta"),
        help_text=_("Nombre descriptivo único para identificar la consulta")
    )
    
    descripcion = models.TextField(
        blank=True,
        verbose_name=_("Descripción"),
        help_text=_("Explicación de qué hace esta consulta y para qué sirve")
    )
    
    select_clause = models.TextField(
        verbose_name=_("Cláusula SELECT"),
        help_text=_("Campos a seleccionar con sus alias. Ej: a.Nombre AS Producto, p.Precio AS PrecioUnitario")
    )
    
    from_clause = models.TextField(
        verbose_name=_("Cláusula FROM"),
        help_text=_("Tabla base y JOINs. Ej: FROM dbo.Precios AS p INNER JOIN dbo.Articulos AS a ON p.id_articulo = a.id")
    )
    
    where_clause = models.TextField(
        blank=True,
        verbose_name=_("Cláusula WHERE"),
        help_text=_("Condiciones con parámetros dinámicos. Ej: WHERE a.Estado = %1 AND p.Precio > %2")
    )
    
    activa = models.BooleanField(
        default=True,
        verbose_name=_("Consulta activa"),
        help_text=_("Solo las consultas activas están disponibles para usuarios finales")
    )
    
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Fecha de creación")
    )
    
    fecha_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Fecha de modificación")
    )
    
    creado_por = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Creado por"),
        help_text=_("Usuario que creó esta consulta")
    )
    
    class Meta:
        db_table = 'dynamic_queries'
        verbose_name = _("Consulta Dinámica")
        verbose_name_plural = _("Consultas Dinámicas")
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['activa']),
            models.Index(fields=['nombre']),
            models.Index(fields=['-fecha_modificacion']),
        ]
    
    def __str__(self):
        return self.nombre
    
    def clean(self):
        """
        Validaciones personalizadas del modelo
        """
        super().clean()
        
        # Validar que SELECT no esté vacío
        if not self.select_clause or not self.select_clause.strip():
            raise ValidationError({
                'select_clause': _('La cláusula SELECT no puede estar vacía')
            })
        
        # Validar que FROM no esté vacío
        if not self.from_clause or not self.from_clause.strip():
            raise ValidationError({
                'from_clause': _('La cláusula FROM no puede estar vacía')
            })
        
        # Validar que no contenga comandos peligrosos
        dangerous_keywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'TRUNCATE', 'EXEC', 'EXECUTE']
        full_query = f"{self.select_clause} {self.from_clause} {self.where_clause}".upper()
        
        for keyword in dangerous_keywords:
            if keyword in full_query:
                raise ValidationError({
                    '__all__': _(f'No se permiten comandos {keyword} en las consultas')
                })
    
    def save(self, *args, **kwargs):
        """
        Sobrescribir save para ejecutar validaciones
        """
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_full_query(self):
        """
        Retorna la consulta completa sin parámetros (para preview)
        """
        query_parts = [
            f"SELECT {self.select_clause.strip()}",
            self.from_clause.strip()
        ]
        
        if self.where_clause and self.where_clause.strip():
            query_parts.append(f"WHERE {self.where_clause.strip()}")
        
        return "\n".join(query_parts)
    
    def get_column_aliases(self):
        """
        Extrae los alias de columnas del SELECT
        
        Returns:
            list: Lista de alias encontrados
        """
        import re
        
        # Buscar patrones: "campo AS alias" o "campo alias"
        pattern = r'\bAS\s+(\w+)|\b(\w+)\s*$'
        matches = re.findall(pattern, self.select_clause, re.IGNORECASE)
        
        aliases = []
        for match in matches:
            alias = match[0] if match[0] else match[1]
            if alias and alias.upper() not in ['FROM', 'WHERE', 'JOIN', 'ON']:
                aliases.append(alias)
        
        return aliases
    
    @property
    def total_parametros(self):
        """
        Retorna el número total de parámetros configurados
        """
        return self.parametros.count()
    
    @property
    def parametros_visibles(self):
        """
        Retorna solo los parámetros visibles para el usuario final
        """
        return self.parametros.filter(visible=True).order_by('orden')