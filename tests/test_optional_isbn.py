"""Books without ISBNs can coexist; supplied ISBNs still identify one title."""
from html.parser import HTMLParser

from models import Book
from tests.conftest import login


class _ISBNInput(HTMLParser):
    attrs = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'input' and attrs.get('name') == 'isbn':
            self.attrs = attrs


def test_add_multiple_books_without_isbn(client, db, admin):
    login(client, 'admin', 'adminpass')
    for i, extra in enumerate(({}, {'isbn': ''}, {'isbn': '   '})):
        response = client.post('/admin/books/add', data={
            'title': f'No ISBN {i}', 'author': 'Author', 'quantity': '2', **extra,
        })
        assert response.status_code == 302

    books = Book.query.order_by(Book.id).all()
    assert len(books) == 3
    assert all(book.isbn is None for book in books)
    assert all(book.available_quantity == 2 for book in books)

    for url in ('/admin/books', f'/admin/books/{books[0].id}/edit'):
        response = client.get(url)
        parser = _ISBNInput()
        parser.feed(response.get_data(as_text=True))
        assert parser.attrs is not None
        assert 'required' not in parser.attrs
        assert parser.attrs['value'] == ''
        assert 'ISBN (optional)' in response.get_data(as_text=True)


def test_clear_isbn_then_assign_it_to_another_book(client, db, admin, book):
    other = Book(title='Other', author='Author', quantity=1, available_quantity=1)
    db.session.add(other)
    db.session.commit()
    original_isbn = book.isbn
    login(client, 'admin', 'adminpass')

    response = client.post(f'/admin/books/{book.id}/edit', data={
        'title': book.title, 'author': book.author, 'isbn': '  ', 'quantity': '1',
    })
    assert response.status_code == 302
    assert db.session.get(Book, book.id).isbn is None

    response = client.post(f'/admin/books/{other.id}/edit', data={
        'title': other.title, 'author': other.author,
        'isbn': f' {original_isbn} ', 'quantity': '1',
    })
    assert response.status_code == 302
    assert db.session.get(Book, other.id).isbn == original_isbn

    response = client.post('/admin/books/add', data={
        'title': 'Duplicate', 'author': 'Author', 'isbn': original_isbn,
    })
    assert 'already exists' in response.get_data(as_text=True)
    assert Book.query.count() == 2


def test_missing_isbn_renders_cleanly_for_members(client, db, member):
    db.session.add(Book(title='Without ISBN', author='Author',
                        quantity=1, available_quantity=1))
    db.session.commit()
    login(client, 'member', 'memberpass')
    response = client.get('/search')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Without ISBN' in html
    assert 'ISBN None' not in html

