document.addEventListener('DOMContentLoaded', function() {
    // Search functionality
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            // Add form validation here
            this.submit();
        });
    }

    // Borrow book functionality
    const borrowButtons = document.querySelectorAll('.borrow-button');
    borrowButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to borrow this book?')) {
                e.preventDefault();
            }
        });
    });

    // Borrowing history
    const borrowingHistoryTable = document.getElementById('borrowing-history-table');
    if (borrowingHistoryTable) {
        // Add sorting functionality if needed
    }
});
