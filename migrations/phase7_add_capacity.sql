-- Phase 7 資料庫遷移腳本
-- 新增 capacity 欄位到 exams 表

-- 檢查並新增 capacity 欄位
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'exams' AND column_name = 'capacity'
    ) THEN
        ALTER TABLE exams ADD COLUMN capacity INTEGER DEFAULT 5 NOT NULL;
        RAISE NOTICE 'Added capacity column to exams table';
    ELSE
        RAISE NOTICE 'capacity column already exists';
    END IF;
END $$;

-- 更新預設值
UPDATE exams SET capacity = 3 WHERE exam_code = 'REG' AND capacity = 5;
UPDATE exams SET capacity = 5 WHERE exam_code = 'PHY' AND capacity = 5;
UPDATE exams SET capacity = 4 WHERE exam_code = 'BLOOD' AND capacity = 5;
UPDATE exams SET capacity = 2 WHERE exam_code = 'XRAY' AND capacity = 5;
UPDATE exams SET capacity = 3 WHERE exam_code = 'US' AND capacity = 5;
UPDATE exams SET capacity = 1 WHERE exam_code = 'CT' AND capacity = 5;
UPDATE exams SET capacity = 1 WHERE exam_code = 'MRI' AND capacity = 5;
UPDATE exams SET capacity = 2 WHERE exam_code = 'ENDO' AND capacity = 5;
UPDATE exams SET capacity = 3 WHERE exam_code = 'CARDIO' AND capacity = 5;
UPDATE exams SET capacity = 4 WHERE exam_code = 'CONSULT' AND capacity = 5;

-- 確認結果
SELECT exam_code, name, capacity FROM exams ORDER BY exam_code;
