"""
Modelo para parámetros de consultas
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _


class QueryParameter(models.Model):
    """
    Parámetro configurable de una consulta dinámica.
    
    Define cómo se debe capturar y validar cada parámetro
    que el usuario final proporcionará al ejecutar la consulta.
    """
    
    TIPO_CHOICES = [
        ('texto', _('Texto')),
        ('numero', _('Número Entero')),
        ('decimal', _('Número Decimal')),
        ('fecha', _('Fecha')),
        ('boolean', _('Sí/No')),
    ]
    
    query = models.ForeignKey(
        'DynamicQuery',
        on_delete=models.CASCADE,
        related_name='parametros',
        verbose_name=_("Consulta")
    )
    
    nombre_interno = models.CharField(
        max_length=100,
        verbose_name=_("Nombre interno"),
        help_text=_("Nombre técnico del campo. Ej: estado_articulo, precio_minimo")
    )
    
    etiqueta_usuario = models.CharField(
        max_length=255,
        verbose_name=_("Etiqueta para usuario"),
        help_text=_("Texto que verá el usuario final. Ej: Estado del Artículo, Precio Mínimo")
    )
    
    tipo_dato = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='texto',
        verbose_name=_("Tipo de dato")
    )
    
    orden = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Orden de aparición"),
        help_text=_("Define el orden en el formulario (menor número aparece primero)")
    )
    
    visible = models.BooleanField(
        default=True,
        verbose_name=_("Visible para usuario final"),
        help_text=_("Si está desmarcado, el parámetro no se mostrará en el formulario")
    )
    
    requerido = models.BooleanField(
        default=False,
        verbose_name=_("Campo obligatorio"),
        help_text=_("Si está marcado, el usuario debe proporcionar un valor")
    )
    
    valor_por_defecto = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Valor por defecto"),
        help_text=_("Valor inicial del campo (opcional)")
    )
    
    placeholder = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Texto de ayuda"),
        help_text=_("Ejemplo o descripción breve que aparece en el campo. Ej: Ingrese un valor mayor a 0")
    )
    
    posicion_where = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_("Posición en WHERE"),
        help_text=_("Número que corresponde al %N en la cláusula WHERE. Ej: 1 para %1, 2 para %2")
    )
    
    class Meta:
        db_table = 'query_parameters'
        verbose_name = _("Parámetro de Consulta")
        verbose_name_plural = _("Parámetros de Consultas")
        ordering = ['query', 'orden']
        unique_together = [
            ('query', 'posicion_where'),
            ('query', 'nombre_interno'),
        ]
        indexes = [
            models.Index(fields=['query', 'orden']),
            models.Index(fields=['query', 'visible']),
        ]
    
    def __str__(self):
        return f"{self.query.nombre} - {self.etiqueta_usuario} (%{self.posicion_where})"
    
    def clean(self):
        """
        Validaciones personalizadas
        """
        super().clean()
        
        # Validar que el nombre interno no tenga espacios
        if self.nombre_interno and ' ' in self.nombre_interno:
            raise ValidationError({
                'nombre_interno': _('El nombre interno no puede contener espacios. Use guiones bajos (_)')
            })
        
        # Validar que la etiqueta no esté vacía
        if not self.etiqueta_usuario or not self.etiqueta_usuario.strip():
            raise ValidationError({
                'etiqueta_usuario': _('La etiqueta para el usuario no puede estar vacía')
            })
        
        # Validar valor por defecto según tipo de dato
        if self.valor_por_defecto:
            self._validar_valor_por_defecto()
    
    def _validar_valor_por_defecto(self):
        """
        Valida que el valor por defecto sea compatible con el tipo de dato
        """
        valor = self.valor_por_defecto.strip()
        
        try:
            if self.tipo_dato == 'numero':
                int(valor)
            elif self.tipo_dato == 'decimal':
                float(valor)
            elif self.tipo_dato == 'fecha':
                from django.utils.dateparse import parse_date
                if not parse_date(valor):
                    raise ValueError()
            elif self.tipo_dato == 'boolean':
                if valor.lower() not in ['true', 'false', '1', '0', 'si', 'no']:
                    raise ValueError()
        except (ValueError, TypeError):
            raise ValidationError({
                'valor_por_defecto': _(f'El valor por defecto no es válido para el tipo {self.get_tipo_dato_display()}')
            })
    
    def save(self, *args, **kwargs):
        """
        Sobrescribir save para ejecutar validaciones
        """
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_form_field_type(self):
        """
        Retorna el tipo de campo HTML apropiado
        """
        field_types = {
            'texto': 'text',
            'numero': 'number',
            'decimal': 'number',
            'fecha': 'date',
            'boolean': 'checkbox',
        }
        return field_types.get(self.tipo_dato, 'text')
    
    def format_value(self, value):
        """
        Formatea el valor según el tipo de dato para SQL
        
        Args:
            value: Valor a formatear
        
        Returns:
            str: Valor formateado para SQL
        """
        if value is None or value == '':
            return None
        
        if self.tipo_dato == 'texto':
            # Escapar comillas simples
            escaped = str(value).replace("'", "''")
            return f"'{escaped}'"
        elif self.tipo_dato == 'numero':
            return str(int(value))
        elif self.tipo_dato == 'decimal':
            return str(float(value))
        elif self.tipo_dato == 'fecha':
            return f"'{value}'"
        elif self.tipo_dato == 'boolean':
            return '1' if value in [True, 'true', '1', 'True', 'si', 'Si'] else '0'
        
        return f"'{value}'"