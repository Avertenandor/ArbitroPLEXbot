-- Initialize PLEX payment requirements for existing deposits
INSERT INTO plex_payment_requirements (
    user_id, deposit_id, daily_plex_required,
    next_payment_due, warning_due, block_due,
    status, total_paid_plex, days_paid, warning_count, is_work_active,
    created_at, updated_at
)
SELECT
    d.user_id,
    d.id,
    d.amount * 10,
    NOW(), NOW(), NOW(),
    'active', 0, 0, 0, true,
    NOW(), NOW()
FROM deposits d
LEFT JOIN plex_payment_requirements p ON d.id = p.deposit_id
WHERE d.status = 'confirmed' AND p.id IS NULL;
