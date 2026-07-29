// Common JavaScript — auto-dismiss alerts, tooltips, etc.
document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss only non-critical flash alerts (success/info) after 6s.
    // Warnings and errors stay until the user dismisses them so they aren't
    // missed by slower or assistive-technology readers.
    const alerts = document.querySelectorAll('.alert-dismissible.alert-success, .alert-dismissible.alert-info');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 6000);
    });

    // Enable Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(function(el) {
        new bootstrap.Tooltip(el);
    });
});