-- Initialize PLEX payment requirements for existing bonus credits
-- Run this AFTER the migration that adds bonus_credit_id column

INSERT INTO plex_payment_requirements (
    user_id, 
    bonus_credit_id, 
    daily_plex_required,
    next_payment_due, 
    warning_due, 
    block_due,
    status, 
    total_paid_plex, 
    days_paid, 
    warning_count, 
    is_work_active,
    created_at, 
    updated_at
)
SELECT 
    bc.user_id, 
    bc.id,  -- bonus_credit_id
    bc.amount * 10,  -- daily_plex_required
    NOW(), 
    NOW(), 
    NOW(),
    'active', 
    0, 
    0, 
    0, 
    true,
    NOW(), 
    NOW()
FROM bonus_credits bc
LEFT JOIN plex_payment_requirements p ON bc.id = p.bonus_credit_id
WHERE bc.is_active = true 
  AND bc.is_roi_completed = false
  AND p.id IS NULL;
