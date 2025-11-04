/**
 * SCRIPTS PRINCIPALES
 * Sistema de Consultas SQL
 */

// Funciones globales
document.addEventListener('DOMContentLoaded', function() {
    console.log('Sistema de Consultas SQL - Iniciado');
    
    // Auto-cerrar alertas
    initAlertAutoClose();
    
    // Inicializar tooltips si existen
    initTooltips();
    
    // Confirmar acciones destructivas
    initConfirmActions();
});

/**
 * Auto-cerrar alertas después de 5 segundos
 */
function initAlertAutoClose() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'all 0.3s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-20px)';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
        
        // Cerrar al hacer clic
        alert.style.cursor = 'pointer';
        alert.addEventListener('click', function() {
            this.style.opacity = '0';
            this.style.transform = 'translateY(-20px)';
            setTimeout(() => this.remove(), 300);
        });
    });
}

/**
 * Inicializar tooltips
 */
function initTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    // Implementar lógica de tooltips si es necesario
}

/**
 * Confirmar acciones destructivas
 */
function initConfirmActions() {
    const deleteButtons = document.querySelectorAll('[data-confirm]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm') || '¿Está seguro de realizar esta acción?';
            if (!confirm(message)) {
                e.preventDefault();
                return false;
            }
        });
    });
}

/**
 * Mostrar/Ocultar secciones
 */
function toggleSection(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.classList.toggle('hidden');
    }
}

/**
 * Copiar texto al portapapeles
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copiado al portapapeles', 'success');
    }).catch(() => {
        showToast('Error al copiar', 'error');
    });
}

/**
 * Mostrar notificación toast
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type}`;
    toast.style.position = 'fixed';
    toast.style.top = '20px';
    toast.style.right = '20px';
    toast.style.zIndex = '9999';
    toast.style.minWidth = '300px';
    toast.innerHTML = `
        <div class="alert-icon">
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        </div>
        <div>${message}</div>
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(400px)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}