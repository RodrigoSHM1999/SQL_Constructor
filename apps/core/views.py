"""
Vistas generales del sistema
"""
from django.shortcuts import render
from django.views import View


class HomeView(View):
    """
    Página de inicio del sistema
    """
    template_name = 'home.html'
    
    def get(self, request):
        from apps.queries.models import DynamicQuery
        
        # Estadísticas básicas
        total_queries = DynamicQuery.objects.count()
        active_queries = DynamicQuery.objects.filter(activa=True).count()
        
        context = {
            'total_queries': total_queries,
            'active_queries': active_queries,
        }
        return render(request, self.template_name, context)