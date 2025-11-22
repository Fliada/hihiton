-- Включаем pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- 1) Банки
CREATE TABLE banks (
    id   SERIAL PRIMARY KEY,
    bank TEXT NOT NULL UNIQUE
);

-- 2) Продукты / услуги
CREATE TABLE products (
    id      SERIAL PRIMARY KEY,
    product TEXT NOT NULL
    -- UNIQUE не ставлю, т.к. в списке есть дубли (например "рефинансирование")
);

-- 3) СЫРЫЕ данные по банкам/продуктам
CREATE TABLE bank_buffer (
    id         BIGSERIAL PRIMARY KEY,
    bank_id    INTEGER NOT NULL REFERENCES banks(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    raw_data   TEXT    NOT NULL,
    source     TEXT    NOT NULL,          -- источник данных
    ts         TIMESTAMPTZ NOT NULL DEFAULT (timezone('utc', now()))
    -- Если захочешь запретить дубликаты по банку/продукту/источнику/времени:
    -- ,CONSTRAINT bank_buffer_unique UNIQUE (bank_id, product_id, source, ts)
);

-- Индексы для ускорения запросов по банку/продукту
CREATE INDEX idx_bank_product_raw_bank_id ON bank_buffer (bank_id);
CREATE INDEX idx_bank_product_raw_product_id ON bank_buffer (product_id);
CREATE INDEX idx_bank_product_raw_bank_product ON bank_buffer (bank_id, product_id);

-- Функция очистки старых записей из bank_buffer (старше 7 дней)
CREATE OR REPLACE FUNCTION bank_buffer_cleanup()
RETURNS trigger AS $$
BEGIN
    DELETE FROM bank_buffer
    WHERE ts < (timezone('utc', now()) - INTERVAL '7 days');
    RETURN NULL;  -- AFTER STATEMENT-триггеру возвращаем NULL
END;
$$ LANGUAGE plpgsql;

-- Триггер, который запускает очистку после каждого INSERT в bank_buffer
CREATE TRIGGER trg_bank_buffer_cleanup
AFTER INSERT ON bank_buffer
FOR EACH STATEMENT
EXECUTE FUNCTION bank_buffer_cleanup();

-- 4) Выделенные критерии (эмбеддинги)
CREATE TABLE bank_analysis (
    id             BIGSERIAL PRIMARY KEY,
    bank_id        INTEGER NOT NULL REFERENCES banks(id) ON DELETE CASCADE,
    product_id     INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    criterion      TEXT    NOT NULL,               -- текст критерия
    criterion_embed VECTOR  NOT NULL,                       -- эмбеддинг критерия
    source         TEXT    NOT NULL,               -- источник
    ts             TIMESTAMPTZ NOT NULL            -- время (UTC, без мс)
);

CREATE INDEX idx_bank_product_criteria_bank_id ON bank_analysis (bank_id);
CREATE INDEX idx_bank_product_criteria_product_id ON bank_analysis (product_id);
CREATE INDEX idx_bank_product_criteria_bank_product ON bank_analysis (bank_id, product_id);
