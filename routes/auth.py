from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError
from urllib.parse import urlparse
from models import User
from extensions import db
from validation import length_errors

bp = Blueprint('auth', __name__)


def _is_safe_next(target):
    """Only allow same-site relative redirects (no scheme, no host, no //)."""
    if not target:
        return False
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return False
    # Reject scheme-relative ("//host") and backslash tricks.
    if not target.startswith('/') or target.startswith('//') or target.startswith('/\\'):
        return False
    return True


def _dashboard_for(user):
    return url_for('admin.dashboard') if user.is_admin else url_for('member.dashboard')


def _landing_for(user):
    """Where a just-authenticated user lands: the one-time welcome walkthrough
    for a member who hasn't finished or skipped it yet, their dashboard
    otherwise. Admins never get routed here -- see models.py:onboarding_completed_at."""
    if not user.is_admin and user.onboarding_completed_at is None:
        return url_for('member.welcome')
    return _dashboard_for(user)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(_dashboard_for(current_user))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not username or not password:
            flash('Please enter both username and password.', 'warning')
            return render_template('login.html')
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash('Invalid username or password.', 'danger')
            # Hand the username back, the way register.html already does for
            # every one of its fields. Retyping it is pure tax -- the wrong
            # half was the password, and this is a phone-first product.
            return render_template('login.html', username=username)
        remember = request.form.get('remember') == 'on'
        login_user(user, remember=remember)
        next_page = request.args.get('next')
        if not _is_safe_next(next_page):
            next_page = _landing_for(user)
        # "Welcome back" is false on a first sign-in, and it landed stacked
        # directly above the onboarding card's own "Welcome, <name>" -- two
        # greetings, one of them wrong, on the screen whose whole job is a
        # first impression. A member who hasn't finished onboarding is going
        # straight to that card, so let it do the greeting alone.
        if user.is_admin or user.onboarding_completed_at is not None:
            flash(f'Welcome back, {user.username}!', 'success')
        return redirect(next_page)
    return render_template('login.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('member.dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        # Collected per field rather than flashed one at a time, so the message
        # renders against the input it is about. Before this every error was a
        # page-top flash with no aria-invalid anywhere, and autofocus sent
        # focus back to username even when the password was the problem.
        field_errors = {}
        if not username:
            field_errors['username'] = 'Choose a username to sign in with.'
        if not email:
            field_errors['email'] = 'Enter an email address.'
        if not password:
            field_errors['password'] = 'Choose a password.'

        for message in length_errors(User, {'username': username, 'email': email}):
            field = 'username' if 'sername' in message else 'email'
            field_errors.setdefault(field, message)

        min_len = current_app.config['MIN_PASSWORD_LENGTH']
        if password and len(password) < min_len:
            field_errors['password'] = (
                f'That is {len(password)} character{"s" if len(password) != 1 else ""} — '
                f'passwords need at least {min_len}.')
        if username and 'username' not in field_errors and \
                User.query.filter_by(username=username).first():
            field_errors['username'] = 'That username is taken — try another.'
        if email and 'email' not in field_errors and \
                User.query.filter_by(email=email).first():
            field_errors['email'] = ('That email is already registered. '
                                     'Sign in instead?')

        if field_errors:
            count = len(field_errors)
            flash(f"Account not created — {count} field{'s need' if count != 1 else ' needs'} "
                  'fixing below.', 'warning')
            return render_template('register.html', username=username, email=email,
                                   field_errors=field_errors)
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            # The pre-checks above (two SELECTs) are not atomic with this
            # INSERT -- two submits for the same username/email racing each
            # other (a double-tap, or the same form open in two tabs) can
            # both pass the SELECTs before either commits. The table's own
            # unique constraint is the real guard; this just turns its
            # failure into the same friendly flash the pre-check gives,
            # instead of an unhandled 500.
            db.session.rollback()
            flash('That username or email is already registered.', 'warning')
            return render_template('register.html', username=username, email=email)
        # Straight in, no separate login step -- the account exists and the
        # password was just typed once; asking for it again buys nothing.
        login_user(user)
        return redirect(url_for('member.welcome'))
    return render_template('register.html')


# ---- Desk-issued password reset ---------------------------------------------
#
# Redemption half of the flow. The issuing half lives in routes/admin.py, on the
# member's detail page, because the librarian is the one who identifies the
# person standing in front of them -- the app cannot, and an emailed link would
# need SMTP this deployment deliberately does without (see
# models.User.issue_reset_code).

@bp.route('/reset', methods=['GET', 'POST'])
def reset_password():
    if current_user.is_authenticated:
        return redirect(_dashboard_for(current_user))

    # Prefilled when the librarian hands over the link rather than reading the
    # code aloud; harmless if absent.
    prefill_code = request.args.get('code', '').strip()
    prefill_user = request.args.get('u', '').strip()

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        code = request.form.get('code', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        field_errors = {}
        if not username:
            field_errors['username'] = 'Enter the username you sign in with.'
        if not code:
            field_errors['code'] = 'Enter the code the library desk gave you.'
        min_len = current_app.config['MIN_PASSWORD_LENGTH']
        if not password:
            field_errors['password'] = 'Choose a new password.'
        elif len(password) < min_len:
            field_errors['password'] = (
                f'That is {len(password)} character{"s" if len(password) != 1 else ""} — '
                f'passwords need at least {min_len}.')
        elif password != confirm:
            field_errors['confirm'] = "The two passwords don't match."

        user = User.query.filter_by(username=username).first() if username else None

        # One message for "no such user", "wrong code" and "expired code". They
        # are the same failure to the person at the keyboard, and telling them
        # apart would let anyone probe which usernames exist and whether a
        # given account currently has a reset outstanding.
        if not field_errors and (user is None or not user.check_reset_code(code)):
            field_errors['code'] = (
                "That code isn't valid, or it has expired. Codes last "
                f'{User.RESET_TTL_MINUTES} minutes — ask the desk for a new one.')

        if field_errors:
            return render_template('reset_password.html', field_errors=field_errors,
                                   username=username, code=code)

        # set_password() clears the reset itself, so the code is single-use by
        # construction rather than by remembering to clear it here.
        user.set_password(password)
        db.session.commit()
        flash('Your password is set. You can sign in with it now.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', field_errors={},
                           username=prefill_user, code=prefill_code)
