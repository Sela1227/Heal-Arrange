-- 系統設定資料表
-- 如果 Railway 沒有自動建立，請手動執行此 SQL

CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    description VARCHAR(255),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER
);

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_system_settings_key ON system_settings(key);

-- 插入預設值（可選）
INSERT INTO system_settings (key, value, description)
VALUES ('default_user_role', 'leader', '新用戶預設角色（pending/coordinator/dispatcher/leader）')
ON CONFLICT (key) DO NOTHING;
