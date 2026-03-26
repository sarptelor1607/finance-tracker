async function deleteTransaction(id, row) {
    if (!confirm('Delete this transaction?')) return;
    const res = await fetch(`/transactions/${id}`, { method: 'DELETE' });
    if (res.ok) row.remove();
}

document.addEventListener('DOMContentLoaded', () => {
    const dateInput = document.getElementById('date');
    if (dateInput && !dateInput.value) {
        dateInput.value = new Date().toISOString().split('T')[0];
    }
});
