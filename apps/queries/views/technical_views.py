"""
Vistas para la interfaz técnica (creación y gestión de consultas)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views import View
from django.views.generic import ListView
from django.urls import reverse_lazy
from django.db import transaction

from ..models import DynamicQuery, QueryParameter
from ..services import (
    QueryValidatorService,
    FromParserService,
    QueryExecutorService,
    QueryBuilderService
)
import json


class QueryListView(ListView):
    """
    Lista todas las consultas creadas (activas e inactivas)
    """
    model = DynamicQuery
    template_name = 'queries/technical/query_list.html'
    context_object_name = 'queries'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = DynamicQuery.objects.all().order_by('-fecha_modificacion')
        
        # Filtro por búsqueda
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(nombre__icontains=search)
        
        # Filtro por estado
        status = self.request.GET.get('status')
        if status == 'activa':
            queryset = queryset.filter(activa=True)
        elif status == 'inactiva':
            queryset = queryset.filter(activa=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['status'] = self.request.GET.get('status', '')
        return context


class QueryCreateView(View):
    """
    Crear una nueva consulta SQL dinámica
    """
    template_name = 'queries/technical/query_create.html'
    
    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        try:
            # Obtener datos del formulario
            nombre = request.POST.get('nombre', '').strip()
            descripcion = request.POST.get('descripcion', '').strip()
            select_clause = request.POST.get('select_clause', '').strip()
            from_clause = request.POST.get('from_clause', '').strip()
            where_clause = request.POST.get('where_clause', '').strip()
            activa = request.POST.get('activa') == 'on'
            
            # Validar campos requeridos
            if not nombre:
                messages.error(request, 'El nombre de la consulta es obligatorio')
                return render(request, self.template_name, {'form_data': request.POST})
            
            if not select_clause:
                messages.error(request, 'La cláusula SELECT es obligatoria')
                return render(request, self.template_name, {'form_data': request.POST})
            
            if not from_clause:
                messages.error(request, 'La cláusula FROM es obligatoria')
                return render(request, self.template_name, {'form_data': request.POST})
            
            # Validar seguridad de la consulta
            validation = QueryValidatorService.validate_full_query(
                select_clause, from_clause, where_clause
            )
            
            if not validation['valid']:
                for error in validation['errors']:
                    messages.error(request, error)
                return render(request, self.template_name, {'form_data': request.POST})
            
            # Crear la consulta
            with transaction.atomic():
                query = DynamicQuery.objects.create(
                    nombre=nombre,
                    descripcion=descripcion,
                    select_clause=select_clause,
                    from_clause=from_clause,
                    where_clause=where_clause,
                    activa=activa,
                    creado_por=request.user.username if request.user.is_authenticated else 'system'
                )
                
                # Procesar parámetros si existen
                self._create_parameters(request, query, validation['parameter_positions'])
            
            messages.success(request, f'Consulta "{nombre}" creada exitosamente')
            return redirect('queries:technical_query_detail', pk=query.pk)
            
        except Exception as e:
            messages.error(request, f'Error al crear la consulta: {str(e)}')
            return render(request, self.template_name, {'form_data': request.POST})
    
    def _create_parameters(self, request, query, parameter_positions):
        """
        Crea los parámetros de la consulta desde el formulario
        """
        for pos in parameter_positions:
            nombre_interno = request.POST.get(f'param_{pos}_nombre', f'parametro_{pos}')
            etiqueta = request.POST.get(f'param_{pos}_etiqueta', f'Parámetro {pos}')
            tipo_dato = request.POST.get(f'param_{pos}_tipo', 'texto')
            visible = request.POST.get(f'param_{pos}_visible') == 'on'
            requerido = request.POST.get(f'param_{pos}_requerido') == 'on'
            orden = request.POST.get(f'param_{pos}_orden', pos)
            placeholder = request.POST.get(f'param_{pos}_placeholder', '')
            valor_defecto = request.POST.get(f'param_{pos}_default', '')
            
            QueryParameter.objects.create(
                query=query,
                nombre_interno=nombre_interno,
                etiqueta_usuario=etiqueta,
                tipo_dato=tipo_dato,
                orden=int(orden),
                visible=visible,
                requerido=requerido,
                posicion_where=pos,
                placeholder=placeholder,
                valor_por_defecto=valor_defecto
            )


class QueryUpdateView(View):
    """
    Editar una consulta existente
    """
    template_name = 'queries/technical/query_edit.html'
    
    def get(self, request, pk):
        query = get_object_or_404(DynamicQuery, pk=pk)
        parametros = query.parametros.all().order_by('orden')
        
        context = {
            'query': query,
            'parametros': parametros,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, pk):
        query = get_object_or_404(DynamicQuery, pk=pk)
        
        try:
            # Actualizar campos básicos
            query.nombre = request.POST.get('nombre', '').strip()
            query.descripcion = request.POST.get('descripcion', '').strip()
            query.select_clause = request.POST.get('select_clause', '').strip()
            query.from_clause = request.POST.get('from_clause', '').strip()
            query.where_clause = request.POST.get('where_clause', '').strip()
            query.activa = request.POST.get('activa') == 'on'
            
            # Validar
            validation = QueryValidatorService.validate_full_query(
                query.select_clause, query.from_clause, query.where_clause
            )
            
            if not validation['valid']:
                for error in validation['errors']:
                    messages.error(request, error)
                return self.get(request, pk)
            
            # Guardar
            with transaction.atomic():
                query.save()
                
                # Actualizar parámetros
                self._update_parameters(request, query, validation['parameter_positions'])
            
            messages.success(request, f'Consulta "{query.nombre}" actualizada exitosamente')
            return redirect('queries:technical_query_detail', pk=query.pk)
            
        except Exception as e:
            messages.error(request, f'Error al actualizar: {str(e)}')
            return self.get(request, pk)
    
    def _update_parameters(self, request, query, parameter_positions):
        """
        Actualiza los parámetros de la consulta
        """
        # Eliminar parámetros que ya no existen
        query.parametros.exclude(posicion_where__in=parameter_positions).delete()
        
        # Actualizar o crear parámetros
        for pos in parameter_positions:
            nombre_interno = request.POST.get(f'param_{pos}_nombre', f'parametro_{pos}')
            etiqueta = request.POST.get(f'param_{pos}_etiqueta', f'Parámetro {pos}')
            tipo_dato = request.POST.get(f'param_{pos}_tipo', 'texto')
            visible = request.POST.get(f'param_{pos}_visible') == 'on'
            requerido = request.POST.get(f'param_{pos}_requerido') == 'on'
            orden = request.POST.get(f'param_{pos}_orden', pos)
            placeholder = request.POST.get(f'param_{pos}_placeholder', '')
            valor_defecto = request.POST.get(f'param_{pos}_default', '')
            
            QueryParameter.objects.update_or_create(
                query=query,
                posicion_where=pos,
                defaults={
                    'nombre_interno': nombre_interno,
                    'etiqueta_usuario': etiqueta,
                    'tipo_dato': tipo_dato,
                    'orden': int(orden),
                    'visible': visible,
                    'requerido': requerido,
                    'placeholder': placeholder,
                    'valor_por_defecto': valor_defecto
                }
            )


class QueryDetailView(View):
    """
    Ver detalle de una consulta
    """
    template_name = 'queries/technical/query_detail.html'
    
    def get(self, request, pk):
        query = get_object_or_404(DynamicQuery, pk=pk)
        parametros = query.parametros.all().order_by('orden')
        
        # Parsear FROM para vista previa
        from_parsed = FromParserService.parse_from_clause(query.from_clause)
        
        context = {
            'query': query,
            'parametros': parametros,
            'from_parsed': from_parsed,
            'sql_preview': query.get_full_query(),
        }
        return render(request, self.template_name, context)


class QueryTestView(View):
    """
    Probar ejecución de una consulta con valores de prueba
    """
    template_name = 'queries/technical/query_test.html'
    
    def get(self, request, pk):
        query = get_object_or_404(DynamicQuery, pk=pk)
        parametros = query.parametros.filter(visible=True).order_by('orden')
        
        context = {
            'query': query,
            'parametros': parametros,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, pk):
        query = get_object_or_404(DynamicQuery, pk=pk)
        parametros = query.parametros.filter(visible=True).order_by('orden')
        
        try:
            # Recopilar valores de parámetros
            params_dict = {}
            for param in query.parametros.all():
                value = request.POST.get(f'param_{param.posicion_where}')
                if value:
                    params_dict[param.posicion_where] = value
            
            # Ejecutar consulta de prueba
            executor = QueryExecutorService()
            result = executor.execute_test_query(
                query_obj=query,
                test_params=params_dict,
                usuario=request.user.username if request.user.is_authenticated else 'system'
            )
            
            context = {
                'query': query,
                'parametros': parametros,
                'result': result,
                'params_used': params_dict
            }
            
            if result['success']:
                messages.success(
                    request, 
                    f'Consulta ejecutada exitosamente. {result["total_rows"]} resultados en {result["execution_time"]}s'
                )
            else:
                messages.error(request, f'Error: {result["error"]}')
            
            return render(request, self.template_name, context)
            
        except Exception as e:
            messages.error(request, f'Error al ejecutar: {str(e)}')
            context = {
                'query': query,
                'parametros': parametros,
            }
            return render(request, self.template_name, context)


class QueryDeleteView(View):
    """
    Eliminar una consulta
    """
    def post(self, request, pk):
        query = get_object_or_404(DynamicQuery, pk=pk)
        nombre = query.nombre
        
        try:
            query.delete()
            messages.success(request, f'Consulta "{nombre}" eliminada exitosamente')
        except Exception as e:
            messages.error(request, f'Error al eliminar: {str(e)}')
        
        return redirect('queries:technical_query_list')


class QueryToggleStatusView(View):
    """
    Activar/Desactivar una consulta
    """
    def post(self, request, pk):
        query = get_object_or_404(DynamicQuery, pk=pk)
        query.activa = not query.activa
        query.save()
        
        status = 'activada' if query.activa else 'desactivada'
        messages.success(request, f'Consulta "{query.nombre}" {status}')
        
        return redirect('queries:technical_query_list')


# ===== VISTAS AJAX =====

class ValidateQueryAjaxView(View):
    """
    Valida una consulta SQL vía AJAX
    """
    def post(self, request):
        try:
            data = json.loads(request.body)
            select_clause = data.get('select_clause', '')
            from_clause = data.get('from_clause', '')
            where_clause = data.get('where_clause', '')
            
            validation = QueryValidatorService.validate_full_query(
                select_clause, from_clause, where_clause
            )
            
            return JsonResponse(validation)
            
        except Exception as e:
            return JsonResponse({
                'valid': False,
                'errors': [str(e)],
                'warnings': [],
                'parameter_positions': []
            })


class ParseFromAjaxView(View):
    """
    Parsea la cláusula FROM vía AJAX y retorna preview
    """
    def post(self, request):
        try:
            data = json.loads(request.body)
            from_clause = data.get('from_clause', '')
            
            parsed = FromParserService.parse_from_clause(from_clause)
            
            return JsonResponse({
                'success': True,
                'parsed': parsed
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })