"""
Vistas para usuarios finales (ejecución de consultas)
"""
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, FileResponse, Http404
from django.views import View
from django.views.generic import ListView
from django.conf import settings
import os
from django.shortcuts import redirect

from ..models import DynamicQuery
from ..services import QueryExecutorService


class EndUserQueryListView(ListView):
    """
    Lista de consultas activas disponibles para usuarios finales
    """
    model = DynamicQuery
    template_name = 'queries/enduser/query_list.html'
    context_object_name = 'queries'
    paginate_by = 20
    
    def get_queryset(self):
        # Solo consultas activas
        queryset = DynamicQuery.objects.filter(activa=True).order_by('nombre')
        
        # Búsqueda
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(nombre__icontains=search)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        return context


class EndUserQueryExecuteView(View):
    """
    Ejecutar una consulta con parámetros del usuario
    """
    template_name = 'queries/enduser/query_execute.html'
    
    def get(self, request, pk):
        query = get_object_or_404(DynamicQuery, pk=pk, activa=True)
        parametros = query.parametros_visibles
        
        context = {
            'query': query,
            'parametros': parametros,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, pk):
        query = get_object_or_404(DynamicQuery, pk=pk, activa=True)
        parametros = query.parametros_visibles
        
        try:
            # Recopilar parámetros del formulario
            params_dict = {}
            for param in query.parametros.all():
                value = request.POST.get(f'param_{param.posicion_where}')
                # Solo agregar si tiene valor
                if value:
                    params_dict[param.posicion_where] = value
            
            # Obtener página
            page = int(request.POST.get('page', 1))
            page_size = getattr(settings, 'RESULTS_PER_PAGE', 50)
            
            # Ejecutar consulta
            executor = QueryExecutorService()
            result = executor.execute_query(
                query_obj=query,
                params_dict=params_dict,
                page=page,
                page_size=page_size,
                usuario=request.user.username if request.user.is_authenticated else 'anonymous'
            )
            
            context = {
                'query': query,
                'parametros': parametros,
                'result': result,
                'params_used': params_dict,
                'show_results': True
            }
            
            if result['success']:
                messages.success(
                    request, 
                    f'Se encontraron {result["total_rows"]} resultados en {result["execution_time"]}s'
                )
            else:
                messages.error(request, f'Error al ejecutar la consulta: {result["error"]}')
            
            return render(request, self.template_name, context)
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            context = {
                'query': query,
                'parametros': parametros,
            }
            return render(request, self.template_name, context)


class ExportToExcelView(View):
    """
    Exportar resultados a Excel
    """
    def post(self, request, pk):
        query = get_object_or_404(DynamicQuery, pk=pk, activa=True)
        
        try:
            # Recopilar parámetros
            params_dict = {}
            for param in query.parametros.all():
                value = request.POST.get(f'param_{param.posicion_where}')
                if value:
                    params_dict[param.posicion_where] = value
            
            # Exportar
            executor = QueryExecutorService()
            result = executor.export_to_excel(
                query_obj=query,
                params_dict=params_dict,
                usuario=request.user.username if request.user.is_authenticated else 'anonymous'
            )
            
            if result['success']:
                # Descargar archivo
                file_path = result['file_path']
                if os.path.exists(file_path):
                    response = FileResponse(
                        open(file_path, 'rb'),
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                    response['Content-Disposition'] = f'attachment; filename="{result["filename"]}"'
                    return response
                else:
                    messages.error(request, 'Archivo no encontrado')
            else:
                messages.error(request, f'Error al exportar: {result["error"]}')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
        
        return redirect('queries:enduser_query_execute', pk=pk)


class ExportToCSVView(View):
    """
    Exportar resultados a CSV
    """
    def post(self, request, pk):
        query = get_object_or_404(DynamicQuery, pk=pk, activa=True)
        
        try:
            # Recopilar parámetros
            params_dict = {}
            for param in query.parametros.all():
                value = request.POST.get(f'param_{param.posicion_where}')
                if value:
                    params_dict[param.posicion_where] = value
            
            # Exportar
            executor = QueryExecutorService()
            result = executor.export_to_csv(
                query_obj=query,
                params_dict=params_dict,
                usuario=request.user.username if request.user.is_authenticated else 'anonymous'
            )
            
            if result['success']:
                file_path = result['file_path']
                if os.path.exists(file_path):
                    response = FileResponse(
                        open(file_path, 'rb'),
                        content_type='text/csv'
                    )
                    response['Content-Disposition'] = f'attachment; filename="{result["filename"]}"'
                    return response
                else:
                    messages.error(request, 'Archivo no encontrado')
            else:
                messages.error(request, f'Error al exportar: {result["error"]}')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
        
        return redirect('queries:enduser_query_execute', pk=pk)