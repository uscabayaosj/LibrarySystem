from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from models import User
from extensions import db

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
            return render_template('login.html')
        remember = request.form.get('remember') == 'on'
        login_user(user, remember=remember)
        next_page = request.args.get('next')
        if not _is_safe_next(next_page):
            next_page = _dashboard_for(user)
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
        if not all([username, email, password]):
            flash('All fields are required.', 'warning')
            return render_template('register.html', username=username, email=email)
        min_len = current_app.config['MIN_PASSWORD_LENGTH']
        if len(password) < min_len:
            flash(f'Password must be at least {min_len} characters long.', 'warning')
            return render_template('register.html', username=username, email=email)
        if User.query.filter_by(username=username).first():
            flash('That username is already taken. Please choose another.', 'warning')
            return render_template('register.html', username=username, email=email)
        if User.query.filter_by(email=email).first():
            flash('That email address is already registered.', 'warning')
            return render_template('register.html', username=username, email=email)
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html')
