"""Form-field length checks, derived from the model columns themselves.

Every text column in models.py declares a length -- Book.title is
String(200), User.username is String(64), and so on. SQLite treats those as
advisory and stores whatever it is given, so an over-length submission looks
fine in development and in CI. Postgres enforces them, so the same request in
production raises `DataError: value too long for type character varying(200)`
and the user gets an unhandled 500 instead of being told their title is too
long.

Reading the limit off the column rather than repeating it here means the
check cannot drift from the schema: widen the column and the message follows,
with no second place to remember.
"""

# Only fields a person actually types into need a friendly name; anything
# missing falls back to the column name, which is still better than nothing.
FIELD_LABELS = {
    'title': 'Title',
    'author': 'Author',
    'isbn': 'ISBN',
    'category': 'Category',
    'publisher': 'Publisher',
    'username': 'Username',
    'email': 'Email address',
    'phone': 'Phone number',
    'org_name': 'Organization name',
}


def max_length(model, field):
    """The declared character limit for `field`, or None if it is unbounded
    (a Text column) or not a column at all."""
    column = model.__table__.columns.get(field)
    if column is None:
        return None
    return getattr(column.type, 'length', None)


def length_errors(model, values):
    """Messages for every value in `values` that is longer than its column
    allows. `values` maps column name to the submitted string.

    The message names the limit and what was actually submitted, so the fix
    is obvious without counting characters by hand.
    """
    errors = []
    for field, value in values.items():
        if not isinstance(value, str) or not value:
            continue
        limit = max_length(model, field)
        if limit is not None and len(value) > limit:
            label = FIELD_LABELS.get(field, field.replace('_', ' ').capitalize())
            errors.append(
                f'{label} must be {limit} characters or fewer '
                f'(you entered {len(value)}).'
            )
    return errors
