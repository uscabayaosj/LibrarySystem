// Admin JavaScript — confirmation dialogs and interactive elements
document.addEventListener('DOMContentLoaded', function() {
    // Delete confirmation for books
    document.querySelectorAll('.delete-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });

    // Return book confirmation
    document.querySelectorAll('.return-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            if (!confirm('Confirm return? The book will be marked as returned.')) {
                e.preventDefault();
            }
        });
    });
});