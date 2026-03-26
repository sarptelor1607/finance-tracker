function switchView(view) {
    document.getElementById('view-past').style.display = view === 'past' ? 'block' : 'none';
    document.getElementById('view-future').style.display = view === 'future' ? 'block' : 'none';
    document.getElementById('btn-past').classList.toggle('active', view === 'past');
    document.getElementById('btn-future').classList.toggle('active', view === 'future');
}

function deleteTransaction(id, row) {
    const cells = row.querySelectorAll('td');
    cells.forEach(td => td.style.textDecoration = 'line-through');
    cells.forEach(td => td.style.opacity = '0.5');

    const actionCell = row.querySelector('.action-cell');
    const originalBtn = actionCell.querySelector('.delete-btn');
    originalBtn.style.display = 'none';

    const undoBtn = document.createElement('button');
    undoBtn.className = 'undo-btn';
    undoBtn.textContent = 'Undo';
    actionCell.appendChild(undoBtn);

    let cancelled = false;

    undoBtn.addEventListener('click', () => {
        cancelled = true;
        cells.forEach(td => td.style.textDecoration = '');
        cells.forEach(td => td.style.opacity = '');
        undoBtn.remove();
        originalBtn.style.display = '';
    });

    setTimeout(async () => {
        if (cancelled) return;
        const res = await fetch(`/transactions/${id}`, { method: 'DELETE' });
        if (res.ok) row.remove();
    }, 5000);
}

document.addEventListener('DOMContentLoaded', () => {
    const dateInput = document.getElementById('date');
    if (dateInput && !dateInput.value) {
        dateInput.value = new Date().toISOString().split('T')[0];
    }

    const recurringCheck = document.getElementById('recurring');
    if (recurringCheck) {
        recurringCheck.addEventListener('change', () => {
            document.getElementById('interval-wrapper').style.display = recurringCheck.checked ? 'block' : 'none';
        });
    }

    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', e => {
            const username = registerForm.querySelector('[name="username"]').value;
            const password = registerForm.querySelector('[name="password"]').value;
            const errorEl = document.getElementById('inline-error');
            let msg = '';

            if (!/^[a-zA-Z0-9_]+$/.test(username)) msg = 'Username can only contain letters, numbers, and underscores.';
            else if (username.length > 30) msg = 'Username must be 30 characters or fewer.';
            else if (password.length < 6) msg = 'Password must be at least 6 characters.';

            if (msg) {
                e.preventDefault();
                errorEl.textContent = msg;
                errorEl.style.display = 'block';
            }
        });
    }
});
