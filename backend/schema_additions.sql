-- Run this on a PostgreSQL database that was created from ../schema.sql.
-- It adds what the front-end needs that the original schema doesn't have yet.
-- (If you let the backend create the tables itself, you don't need this file.)

-- Category dropdown in the task form (Study, Work, Personal, Health, Other).
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS category VARCHAR(50) NOT NULL DEFAULT 'Other';

-- Drag-and-drop ordering of the task list. Lower numbers appear first.
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS position INTEGER NOT NULL DEFAULT 0;

-- Messages from the contact form on the home page.
CREATE TABLE IF NOT EXISTS contact_messages (
	id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	name VARCHAR(100) NOT NULL,
	email VARCHAR(250) NOT NULL,
	subject VARCHAR(200) NOT NULL,
	message TEXT NOT NULL,
	created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
