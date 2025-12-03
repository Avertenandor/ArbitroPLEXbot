INSERT INTO admins (telegram_id, username, role, is_active, created_at, updated_at) 
VALUES 
  (6540613027, NULL, 'moderator', true, NOW(), NOW()),
  (1691026253, NULL, 'moderator', true, NOW(), NOW()),
  (241568583, NULL, 'moderator', true, NOW(), NOW())
ON CONFLICT (telegram_id) DO UPDATE SET role = 'moderator', is_active = true, updated_at = NOW();

