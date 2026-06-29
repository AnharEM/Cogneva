import Database from 'better-sqlite3';
import { env } from '$env/dynamic/private';

const db = new Database(env.DB_PATH || 'auth.sqlite');

// Initialize tables
db.exec(`
	CREATE TABLE IF NOT EXISTS users (
		id TEXT PRIMARY KEY,
		username TEXT UNIQUE NOT NULL,
		password_hash TEXT NOT NULL
	);
	CREATE TABLE IF NOT EXISTS sessions (
		id TEXT PRIMARY KEY,
		user_id TEXT NOT NULL,
		expires_at INTEGER NOT NULL,
		FOREIGN KEY (user_id) REFERENCES users(id)
	);
`);

export const db_instance = db;
