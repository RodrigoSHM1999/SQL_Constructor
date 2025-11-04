"""
Configuración del Django Admin para la app queries
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import DynamicQuery, QueryParameter, QueryExecution


class QueryParameterInline(admin.TabularInline):
    """
    Inline para gestionar parámetros dentro de la consulta
    """
    model = QueryParameter
    extra = 1
    fields = [
        'posicion_where',
        'nombre_interno',
        'etiqueta_usuario',
        'tipo_dato',
        'orden',
        'visible',
        'requerido',
        'valor_por_defecto',
        'placeholder'
    ]
    ordering = ['orden']


@admin.register(DynamicQuery)
class DynamicQueryAdmin(admin.ModelAdmin):
    """
    Administración de Consultas Dinámicas
    """
    list_display = [
        'nombre',
        'activa_badge',
        'total_parametros_display',
        'fecha_modificacion',
        'creado_por',
        'acciones'
    ]
    list_filter = [
        'activa',
        'fecha_creacion',
        'fecha_modificacion'
    ]
    search_fields = [
        'nombre',
        'descripcion',
        'creado_por'
    ]
    readonly_fields = [
        'fecha_creacion',
        'fecha_modificacion',
        'preview_sql',
        'preview_from_parsed'
    ]
    
    fieldsets = (
        ('Información Básica', {
            'fields': (
                'nombre',
                'descripcion',
                'activa',
                'creado_por'
            )
        }),
        ('Definición SQL', {
            'fields': (
                'select_clause',
                'from_clause',
                'where_clause'
            ),
            'description': 'Define la consulta SQL dinámica con sus cláusulas'
        }),
        ('Vista Previa', {
            'fields': (
                'preview_sql',
                'preview_from_parsed'
            ),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': (
                'fecha_creacion',
                'fecha_modificacion'
            ),
            'classes': ('collapse',)
        })
    )
    
    inlines = [QueryParameterInline]
    
    def activa_badge(self, obj):
        """
        Badge de estado activo/inactivo
        """
        if obj.activa:
            return format_html(
                '<span style="background-color: #10b981; color: white; padding: 3px 10px; '
                'border-radius: 12px; font-size: 11px; font-weight: bold;">'
                '✓ ACTIVA</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #ef4444; color: white; padding: 3px 10px; '
                'border-radius: 12px; font-size: 11px; font-weight: bold;">'
                '✗ INACTIVA</span>'
            )
    activa_badge.short_description = 'Estado'
    
    def total_parametros_display(self, obj):
        """
        Muestra total de parámetros
        """
        total = obj.total_parametros
        if total > 0:
            return format_html(
                '<span style="background-color: #3b82f6; color: white; padding: 2px 8px; '
                'border-radius: 10px; font-size: 11px;">{} parámetro(s)</span>',
                total
            )
        return format_html(
            '<span style="color: #9ca3af; font-size: 11px;">Sin parámetros</span>'
        )
    total_parametros_display.short_description = 'Parámetros'
    
    def acciones(self, obj):
        """
        Botones de acción rápida
        """
        test_url = reverse('queries:technical_query_test', args=[obj.pk])
        detail_url = reverse('queries:technical_query_detail', args=[obj.pk])
        execute_url = reverse('queries:enduser_query_execute', args=[obj.pk])
        
        return format_html(
            '<a href="{}" style="background-color: #10b981; color: white; padding: 4px 8px; '
            'border-radius: 4px; text-decoration: none; font-size: 11px; margin-right: 4px;">'
            '🧪 Probar</a>'
            '<a href="{}" style="background-color: #3b82f6; color: white; padding: 4px 8px; '
            'border-radius: 4px; text-decoration: none; font-size: 11px; margin-right: 4px;">'
            '👁️ Ver</a>'
            '<a href="{}" style="background-color: #8b5cf6; color: white; padding: 4px 8px; '
            'border-radius: 4px; text-decoration: none; font-size: 11px;">'
            '▶️ Ejecutar</a>',
            test_url, detail_url, execute_url
        )
    acciones.short_description = 'Acciones'
    
    def preview_sql(self, obj):
        """
        Vista previa del SQL completo
        """
        if obj.pk:
            sql = obj.get_full_query()
            return format_html(
                '<div style="background-color: #1f2937; color: #10b981; padding: 16px; '
                'border-radius: 8px; font-family: monospace; font-size: 12px; '
                'white-space: pre-wrap; overflow-x: auto;">{}</div>',
                sql
            )
        return '-'
    preview_sql.short_description = 'Vista Previa SQL'
    
    def preview_from_parsed(self, obj):
        """
        Vista previa estructurada del FROM
        """
        if obj.pk and obj.from_clause:
            from apps.queries.services import FromParserService
            parsed = FromParserService.parse_from_clause(obj.from_clause)
            
            html_parts = ['<div style="font-family: monospace; font-size: 12px;">']
            
            for item in parsed['preview']:
                color = '#10b981' if item['type'] == 'BASE' else '#3b82f6'
                html_parts.append(
                    f'<div style="padding: 8px; margin: 4px 0; background-color: #f3f4f6; '
                    f'border-left: 4px solid {color}; border-radius: 4px;">'
                    f'<strong>{item["icon"]} {item["type"]}:</strong> '
                    f'<span style="color: {color};">{item["table"]}</span>'
                )
                if item['alias']:
                    html_parts.append(f' <span style="color: #6b7280;">AS {item["alias"]}</span>')
                if item['condition']:
                    html_parts.append(
                        f'<div style="margin-top: 4px; color: #6b7280; font-size: 11px;">'
                        f'ON {item["condition"]}</div>'
                    )
                html_parts.append('</div>')
            
            html_parts.append('</div>')
            
            return mark_safe(''.join(html_parts))
        return '-'
    preview_from_parsed.short_description = 'Vista Previa FROM'
    
    def save_model(self, request, obj, form, change):
        """
        Guardar el usuario que crea/modifica
        """
        if not change:  # Si es creación
            obj.creado_por = request.user.username
        super().save_model(request, obj, form, change)
    
    class Media:
        css = {
            'all': ('admin/css/forms.css',)
        }


@admin.register(QueryParameter)
class QueryParameterAdmin(admin.ModelAdmin):
    """
    Administración de Parámetros de Consultas
    """
    list_display = [
        'query',
        'etiqueta_usuario',
        'nombre_interno',
        'tipo_dato_badge',
        'posicion_where',
        'orden',
        'estado_badges'
    ]
    list_filter = [
        'tipo_dato',
        'visible',
        'requerido',
        'query'
    ]
    search_fields = [
        'nombre_interno',
        'etiqueta_usuario',
        'query__nombre'
    ]
    list_select_related = ['query']
    
    fieldsets = (
        ('Consulta', {
            'fields': ('query',)
        }),
        ('Identificación', {
            'fields': (
                'nombre_interno',
                'etiqueta_usuario',
                'posicion_where'
            )
        }),
        ('Configuración', {
            'fields': (
                'tipo_dato',
                'orden',
                'visible',
                'requerido'
            )
        }),
        ('Valores', {
            'fields': (
                'valor_por_defecto',
                'placeholder'
            ),
            'classes': ('collapse',)
        })
    )
    
    def tipo_dato_badge(self, obj):
        """
        Badge para tipo de dato
        """
        colors = {
            'texto': '#6b7280',
            'numero': '#3b82f6',
            'decimal': '#8b5cf6',
            'fecha': '#10b981',
            'boolean': '#f59e0b'
        }
        color = colors.get(obj.tipo_dato, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 10px; font-size: 11px;">{}</span>',
            color,
            obj.get_tipo_dato_display()
        )
    tipo_dato_badge.short_description = 'Tipo'
    
    def estado_badges(self, obj):
        """
        Badges de estado
        """
        badges = []
        
        if obj.visible:
            badges.append(
                '<span style="background-color: #10b981; color: white; padding: 2px 6px; '
                'border-radius: 8px; font-size: 10px; margin-right: 4px;">👁️ Visible</span>'
            )
        else:
            badges.append(
                '<span style="background-color: #9ca3af; color: white; padding: 2px 6px; '
                'border-radius: 8px; font-size: 10px; margin-right: 4px;">🚫 Oculto</span>'
            )
        
        if obj.requerido:
            badges.append(
                '<span style="background-color: #ef4444; color: white; padding: 2px 6px; '
                'border-radius: 8px; font-size: 10px;">⚠️ Obligatorio</span>'
            )
        
        return format_html(''.join(badges))
    estado_badges.short_description = 'Estado'


@admin.register(QueryExecution)
class QueryExecutionAdmin(admin.ModelAdmin):
    """
    Administración de Ejecuciones (Log de auditoría)
    """
    list_display = [
        'query',
        'usuario',
        'exitosa_badge',
        'total_resultados',
        'tiempo_display',
        'fecha_ejecucion'
    ]
    list_filter = [
        'exitosa',
        'fecha_ejecucion',
        'query'
    ]
    search_fields = [
        'query__nombre',
        'usuario'
    ]
    readonly_fields = [
        'query',
        'usuario',
        'parametros_enviados',
        'total_resultados',
        'tiempo_ejecucion',
        'fecha_ejecucion',
        'exitosa',
        'mensaje_error',
        'sql_ejecutado',
        'parametros_display',
        'sql_preview'
    ]
    list_select_related = ['query']
    date_hierarchy = 'fecha_ejecucion'
    
    fieldsets = (
        ('Información de Ejecución', {
            'fields': (
                'query',
                'usuario',
                'fecha_ejecucion',
                'exitosa'
            )
        }),
        ('Parámetros', {
            'fields': (
                'parametros_display',
                'parametros_enviados'
            )
        }),
        ('Resultados', {
            'fields': (
                'total_resultados',
                'tiempo_ejecucion'
            )
        }),
        ('SQL Ejecutado', {
            'fields': (
                'sql_preview',
                'sql_ejecutado'
            ),
            'classes': ('collapse',)
        }),
        ('Error', {
            'fields': ('mensaje_error',),
            'classes': ('collapse',)
        })
    )
    
    def has_add_permission(self, request):
        """
        No permitir crear ejecuciones desde el admin
        """
        return False
    
    def has_change_permission(self, request, obj=None):
        """
        No permitir editar ejecuciones
        """
        return False
    
    def exitosa_badge(self, obj):
        """
        Badge de ejecución exitosa
        """
        if obj.exitosa:
            return format_html(
                '<span style="background-color: #10b981; color: white; padding: 3px 10px; '
                'border-radius: 12px; font-size: 11px; font-weight: bold;">✓ EXITOSA</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #ef4444; color: white; padding: 3px 10px; '
                'border-radius: 12px; font-size: 11px; font-weight: bold;">✗ ERROR</span>'
            )
    exitosa_badge.short_description = 'Estado'
    
    def tiempo_display(self, obj):
        """
        Tiempo de ejecución formateado
        """
        return obj.get_tiempo_display()
    tiempo_display.short_description = 'Tiempo'
    
    def parametros_display(self, obj):
        """
        Parámetros en formato legible
        """
        if not obj.parametros_enviados:
            return format_html('<span style="color: #9ca3af;">Sin parámetros</span>')
        
        html_parts = ['<table style="width: 100%; font-size: 12px;">']
        html_parts.append('<tr style="background-color: #f3f4f6;"><th style="padding: 8px; text-align: left;">Posición</th><th style="padding: 8px; text-align: left;">Valor</th></tr>')
        
        for key, value in obj.parametros_enviados.items():
            html_parts.append(
                f'<tr><td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>%{key}</strong></td>'
                f'<td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><code>{value}</code></td></tr>'
            )
        
        html_parts.append('</table>')
        
        return mark_safe(''.join(html_parts))
    parametros_display.short_description = 'Parámetros Utilizados'
    
    def sql_preview(self, obj):
        """
        Vista previa del SQL ejecutado
        """
        if obj.sql_ejecutado:
            return format_html(
                '<div style="background-color: #1f2937; color: #10b981; padding: 16px; '
                'border-radius: 8px; font-family: monospace; font-size: 12px; '
                'white-space: pre-wrap; overflow-x: auto;">{}</div>',
                obj.sql_ejecutado
            )
        return '-'
    sql_preview.short_description = 'Vista Previa SQL'


# Personalización del Admin Site
admin.site.site_header = "Sistema de Consultas SQL - Administración"
admin.site.site_title = "SQL Query Manager"
admin.site.index_title = "Panel de Administración"