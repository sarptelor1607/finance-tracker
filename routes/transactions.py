from flask import Blueprint, render_template, request, redirect, session
from models import db, Transaction
from datetime import date, timedelta, datetime
from functools import wraps
import calendar

transactions_bp = Blueprint('transactions', __name__)

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/auth/login')
        return f(*args, **kwargs)
    return wrapper

def next_due(last_date, interval):
    if interval == 'daily':
        return last_date + timedelta(days=1)
    if interval == 'weekly':
        return last_date + timedelta(weeks=1)
    if interval == 'monthly':
        y, m = last_date.year, last_date.month
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
        d = min(last_date.day, calendar.monthrange(y, m)[1])
        return last_date.replace(year=y, month=m, day=d)
    return last_date

def apply_recurring(uid):
    today = date.today()
    recurring = Transaction.query.filter_by(user_id=uid, recurring=True).all()

    latest = {}
    for t in recurring:
        key = (t.type, t.amount, t.category, t.note, t.recurring_interval)
        if key not in latest or t.date > latest[key]:
            latest[key] = t.date

    for key, last_date in latest.items():
        typ, amount, category, note, interval = key
        if next_due(last_date, interval) <= today:
            already = Transaction.query.filter_by(
                user_id=uid, type=typ, amount=amount,
                category=category, note=note, date=today, recurring=True
            ).first()
            if not already:
                db.session.add(Transaction(
                    user_id=uid, type=typ, amount=amount,
                    category=category, date=today, note=note,
                    recurring=True, recurring_interval=interval
                ))
    db.session.commit()

@transactions_bp.route('/dashboard')
@login_required
def dashboard():
    uid = session['user_id']
    apply_recurring(uid)
    all_txns = Transaction.query.filter_by(user_id=uid).all()
    income = sum(t.amount for t in all_txns if t.type == 'income')
    expense = sum(t.amount for t in all_txns if t.type == 'expense')
    savings = sum(t.amount for t in all_txns if t.type == 'saving')
    balance = income - expense
    recent = Transaction.query.filter_by(user_id=uid).order_by(Transaction.date.desc()).limit(5).all()
    error = 'Invalid date. Use DD.MM.YYYY or YYYY-MM-DD.' if request.args.get('error') == 'invalid_date' else None
    return render_template('dashboard.html',
        income=income, expense=expense, balance=balance, savings=savings,
        recent=recent, username=session.get('username'), error=error)

def parse_date(s):
    for fmt in ('%d.%m.%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f'Invalid date: {s}')

@transactions_bp.route('/transactions/add', methods=['POST'])
@login_required
def add():
    try:
        parsed_date = parse_date(request.form['date'])
    except ValueError:
        return redirect('/dashboard?error=invalid_date')
    try:
        recurring = 'recurring' in request.form
        t = Transaction(
            user_id=session['user_id'],
            type=request.form['type'],
            amount=float(request.form['amount']),
            category=request.form['category'],
            date=parsed_date,
            note=request.form.get('note', ''),
            recurring=recurring,
            recurring_interval=request.form.get('recurring_interval') if recurring else None
        )
        db.session.add(t)
        db.session.commit()
    except Exception:
        pass
    return redirect('/dashboard')

@transactions_bp.route('/transactions')
@login_required
def list_transactions():
    uid = session['user_id']
    f = request.args.get('filter')
    today = date.today()

    q = Transaction.query.filter_by(user_id=uid)
    if f == 'daily':
        q = q.filter(Transaction.date == today)
    elif f == 'weekly':
        q = q.filter(Transaction.date >= today - timedelta(days=7))
    elif f == 'monthly':
        q = q.filter(Transaction.date >= today.replace(day=1))

    txns = q.order_by(Transaction.date.desc()).all()
    income = sum(t.amount for t in txns if t.type == 'income')
    expense = sum(t.amount for t in txns if t.type == 'expense')
    savings = sum(t.amount for t in txns if t.type == 'saving')
    return render_template('history.html', transactions=txns, active_filter=f,
        income=income, expense=expense, savings=savings)

@transactions_bp.route('/transactions/<int:tid>', methods=['DELETE'])
@login_required
def delete(tid):
    t = Transaction.query.filter_by(id=tid, user_id=session['user_id']).first()
    if t:
        db.session.delete(t)
        db.session.commit()
    return ('', 204)

@transactions_bp.route('/report')
@login_required
def report():
    uid = session['user_id']
    today = date.today()
    all_txns = Transaction.query.filter_by(user_id=uid).all()
    future_one_time = [t for t in all_txns if not t.recurring and t.date > today]

    rec_seen = {}
    for t in all_txns:
        if not t.recurring:
            continue
        key = (t.type, t.amount, t.category, t.note or '', t.recurring_interval)
        if key not in rec_seen:
            rec_seen[key] = key
    recurring = list(rec_seen.values())

    recurring_summary = []
    for typ, amount, category, note, interval in recurring:
        if interval == 'daily':
            w, m, y = amount * 7, amount * 30.4375, amount * 365
        elif interval == 'weekly':
            w, m, y = amount, amount * 52 / 12, amount * 52
        else:
            w, m, y = amount * 12 / 52, amount, amount * 12
        recurring_summary.append({
            'type': typ, 'amount': amount, 'category': category,
            'note': note, 'interval': interval,
            'weekly': w, 'monthly': m, 'yearly': y,
        })

    def project(amount, interval, days):
        if interval == 'daily':
            return amount * days
        if interval == 'weekly':
            return amount * days / 7
        if interval == 'monthly':
            return amount * days / 30.4375
        return 0

    def build_row(label, period_start, period_end, cumulative):
        days = (period_end - period_start).days + 1
        inc = exp = sav = 0
        for typ, amount, category, note, interval in recurring:
            p = project(amount, interval, days)
            if typ == 'income':   inc += p
            elif typ == 'expense': exp += p
            elif typ == 'saving':  sav += p

        one_time = [t for t in future_one_time if period_start <= t.date <= period_end]
        ot_inc = ot_exp = ot_sav = 0
        for t in one_time:
            if t.type == 'income':   ot_inc += t.amount
            elif t.type == 'expense': ot_exp += t.amount
            elif t.type == 'saving':  ot_sav += t.amount
        inc += ot_inc
        exp += ot_exp
        sav += ot_sav

        net = inc - exp
        cumulative += net
        ot_net = ot_inc - ot_exp
        return {
            'label': label, 'income': inc, 'expense': exp, 'saving': sav,
            'net': net, 'cumulative': cumulative,
            'one_time_count': len(one_time), 'one_time_net': ot_net,
        }, cumulative

    weekly_data = []
    cumulative = 0
    for i in range(4):
        start = today + timedelta(days=i * 7 + 1)
        end = today + timedelta(days=(i + 1) * 7)
        label = f'{start.strftime("%b %d")} – {end.strftime("%b %d")}'
        row, cumulative = build_row(label, start, end, cumulative)
        weekly_data.append(row)

    monthly_data = []
    cumulative = 0
    for i in range(12):
        m = today.month + i + 1
        y = today.year
        while m > 12:
            m -= 12
            y += 1
        days_in_month = calendar.monthrange(y, m)[1]
        start = date(y, m, 1)
        end = date(y, m, days_in_month)
        row, cumulative = build_row(date(y, m, 1).strftime('%b %Y'), start, end, cumulative)
        monthly_data.append(row)

    yearly_data = []
    cumulative = 0
    for i in range(5):
        y = today.year + i + 1
        start = date(y, 1, 1)
        end = date(y, 12, 31)
        row, cumulative = build_row(str(y), start, end, cumulative)
        yearly_data.append(row)

    def past_row(label, period_start, period_end):
        txns = [t for t in all_txns if period_start <= t.date <= period_end]
        inc = sum(t.amount for t in txns if t.type == 'income')
        exp = sum(t.amount for t in txns if t.type == 'expense')
        sav = sum(t.amount for t in txns if t.type == 'saving')
        return {'label': label, 'income': inc, 'expense': exp, 'saving': sav, 'net': inc - exp}

    past_weekly = []
    for i in range(3, -1, -1):
        end = today - timedelta(weeks=i)
        start = end - timedelta(days=6)
        past_weekly.append(past_row(f'{start.strftime("%b %d")} – {end.strftime("%b %d")}', start, end))

    past_monthly = []
    for i in range(11, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        days_in_m = calendar.monthrange(y, m)[1]
        past_monthly.append(past_row(date(y, m, 1).strftime('%b %Y'), date(y, m, 1), date(y, m, days_in_m)))

    past_yearly = []
    for i in range(1, -1, -1):
        y = today.year - i
        past_yearly.append(past_row(str(y), date(y, 1, 1), date(y, 12, 31)))

    return render_template('report.html',
        recurring_summary=recurring_summary,
        weekly=weekly_data, monthly=monthly_data, yearly=yearly_data,
        past_weekly=past_weekly, past_monthly=past_monthly, past_yearly=past_yearly)
