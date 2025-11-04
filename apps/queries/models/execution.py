"""
Modelo para registro de ejecuciones de consultas (auditoría)
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
import json


class QueryExecution(models.Model):
    """
    Registro de cada ejecución de una consulta dinámica.
    
    Útil para auditoría, análisis de uso y debugging.
    """
    
    query = models.ForeignKey(
        'DynamicQuery',
        on_delete=models.CASCADE,
        related_name='ejecuciones',
        verbose_name=_("Consulta")
    )
    
    usuario = models.CharField(
        max_length=100,
        verbose_name=_("Usuario"),
        help_text=_("Usuario que ejecutó la consulta")
    )
    
    parametros_enviados = models.JSONField(
        default=dict,
        verbose_name=_("Parámetros enviados"),
        help_text=_("Valores de parámetros utilizados en la ejecución")
    )
    
    total_resultados = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Total de resultados"),
        help_text=_("Número de filas retornadas por la consulta")
    )
    
    tiempo_ejecucion = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(0)],
        verbose_name=_("Tiempo de ejecución (segundos)")
    )
    
    fecha_ejecucion = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Fecha de ejecución")
    )
    
    exitosa = models.BooleanField(
        default=True,
        verbose_name=_("Ejecución exitosa")
    )
    
    mensaje_error = models.TextField(
        blank=True,
        verbose_name=_("Mensaje de error"),
        help_text=_("Descripción del error si la ejecución falló")
    )
    
    sql_ejecutado = models.TextField(
        blank=True,
        verbose_name=_("SQL ejecutado"),
        help_text=_("Query final que fue ejecutado (para debugging)")
    )
    
    class Meta:
        db_table = 'query_executions'
        verbose_name = _("Ejecución de Consulta")
        verbose_name_plural = _("Ejecuciones de Consultas")
        ordering = ['-fecha_ejecucion']
        indexes = [
            models.Index(fields=['-fecha_ejecucion']),
            models.Index(fields=['query', '-fecha_ejecucion']),
            models.Index(fields=['usuario', '-fecha_ejecucion']),
            models.Index(fields=['exitosa']),
        ]
    
    def __str__(self):
        status = "✓" if self.exitosa else "✗"
        return f"{status} {self.query.nombre} - {self.usuario} ({self.fecha_ejecucion.strftime('%Y-%m-%d %H:%M')})"
    
    def get_parametros_display(self):
        """
        Retorna los parámetros en formato legible
        """
        if not self.parametros_enviados:
            return "Sin parámetros"
        
        return ", ".join([f"{k}: {v}" for k, v in self.parametros_enviados.items()])
    
    def get_tiempo_display(self):
        """
        Retorna el tiempo de ejecución formateado
        """
        tiempo = float(self.tiempo_ejecucion)
        if tiempo < 1:
            return f"{tiempo * 1000:.0f} ms"
        return f"{tiempo:.2f} seg"
    
    @classmethod
    def crear_log(cls, query, usuario, parametros, total_resultados, tiempo_ejecucion, 
                  exitosa=True, mensaje_error='', sql_ejecutado=''):
        """
        Método de clase para crear un log de ejecución fácilmente
        
        Args:
            query: Instancia de DynamicQuery
            usuario: Nombre del usuario
            parametros: Dict con parámetros {posicion: valor}
            total_resultados: Número de filas retornadas
            tiempo_ejecucion: Tiempo en segundos (float o Decimal)
            exitosa: Si la ejecución fue exitosa
            mensaje_error: Mensaje de error si aplicable
            sql_ejecutado: Query SQL final ejecutado
        
        Returns:
            QueryExecution: Instancia creada
        """
        return cls.objects.create(
            query=query,
            usuario=usuario,
            parametros_enviados=parametros,
            total_resultados=total_resultados,
            tiempo_ejecucion=tiempo_ejecucion,
            exitosa=exitosa,
            mensaje_error=mensaje_error,
            sql_ejecutado=sql_ejecutado
        )