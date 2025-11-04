"""
URLs de la aplicación queries
"""
from django.urls import path
from .views import (
    # Technical views
    QueryListView,
    QueryCreateView,
    QueryUpdateView,
    QueryDetailView,
    QueryTestView,
    QueryDeleteView,
    QueryToggleStatusView,
    ValidateQueryAjaxView,
    ParseFromAjaxView,
    
    # End user views
    EndUserQueryListView,
    EndUserQueryExecuteView,
    ExportToExcelView,
    ExportToCSVView,
)

app_name = 'queries'

urlpatterns = [
    # ===== RUTAS PARA TÉCNICOS =====
    path('technical/', QueryListView.as_view(), name='technical_query_list'),
    path('technical/create/', QueryCreateView.as_view(), name='technical_query_create'),
    path('technical/<int:pk>/', QueryDetailView.as_view(), name='technical_query_detail'),
    path('technical/<int:pk>/edit/', QueryUpdateView.as_view(), name='technical_query_edit'),
    path('technical/<int:pk>/test/', QueryTestView.as_view(), name='technical_query_test'),
    path('technical/<int:pk>/delete/', QueryDeleteView.as_view(), name='technical_query_delete'),
    path('technical/<int:pk>/toggle/', QueryToggleStatusView.as_view(), name='technical_query_toggle'),
    
    # AJAX endpoints
    path('ajax/validate/', ValidateQueryAjaxView.as_view(), name='ajax_validate_query'),
    path('ajax/parse-from/', ParseFromAjaxView.as_view(), name='ajax_parse_from'),
    
    # ===== RUTAS PARA USUARIOS FINALES =====
    path('', EndUserQueryListView.as_view(), name='enduser_query_list'),
    path('<int:pk>/', EndUserQueryExecuteView.as_view(), name='enduser_query_execute'),
    path('<int:pk>/export/excel/', ExportToExcelView.as_view(), name='export_excel'),
    path('<int:pk>/export/csv/', ExportToCSVView.as_view(), name='export_csv'),
]