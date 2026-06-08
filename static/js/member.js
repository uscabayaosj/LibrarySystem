// Member JavaScript — borrow and cancel confirmation
document.addEventListener('DOMContentLoaded', function() {
    // Borrow confirmation
    document.querySelectorAll('.borrow-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            if (!confirm('Borrow this book? It will be due in 14 days.')) {
                e.preventDefault();
            }
        });
    });

    // Cancel reservation confirmation
    document.querySelectorAll('.cancel-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            if (!confirm('Cancel this reservation?')) {
                e.preventDefault();
            }
        });
    });
});