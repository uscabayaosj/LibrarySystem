document.addEventListener('DOMContentLoaded', function() {
    // Book management
    const addBookForm = document.getElementById('add-book-form');
    if (addBookForm) {
        addBookForm.addEventListener('submit', function(e) {
            e.preventDefault();
            // Add form validation here
            this.submit();
        });
    }

    const editBookForms = document.querySelectorAll('.edit-book-form');
    editBookForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            // Add form validation here
            this.submit();
        });
    });

    const deleteBookButtons = document.querySelectorAll('.delete-book-button');
    deleteBookButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this book?')) {
                e.preventDefault();
            }
        });
    });

    // Member management
    const memberTable = document.getElementById('member-table');
    if (memberTable) {
        memberTable.addEventListener('click', function(e) {
            if (e.target.classList.contains('delete-member-button')) {
                if (!confirm('Are you sure you want to delete this member?')) {
                    e.preventDefault();
                }
            }
        });
    }

    // Borrowing history
    const borrowingHistoryTable = document.getElementById('borrowing-history-table');
    if (borrowingHistoryTable) {
        // Add sorting functionality if needed
    }
});
