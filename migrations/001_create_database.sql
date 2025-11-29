-- Migration: 001_create_database
-- Description: Create database, user, and initial schema setup
-- Created: 2025-11-28

-- ============================================================
-- STEP 1: Run as postgres superuser to create database
-- ============================================================
-- psql -U postgres -f migrations/001_create_database.sql

-- Create database
CREATE DATABASE saas_risk_scanner;


-- Connect to the new database
\connect saas_risk_scanner

-- ============================================================
-- STEP 2: Create application user and grant privileges
-- ============================================================

-- Create application user (change 'your_secure_password' to a strong password)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_catalog.pg_roles WHERE rolname = 'saas_risk_user'
    ) THEN
        CREATE ROLE saas_risk_user WITH LOGIN PASSWORD 'admin123';
    END IF;
END
$$;

-- Give permissions on the DB
GRANT ALL PRIVILEGES ON DATABASE saas_risk_scanner TO saas_risk_user;

-- Switch to the database (must run manually in psql)
-- \c saas_risk_scanner

-- Give permissions on existing objects
GRANT ALL ON SCHEMA public TO saas_risk_user;
GRANT ALL PRIVILEGES ON ALL TABLES    IN SCHEMA public TO saas_risk_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO saas_risk_user;

-- Ensure permissions for all future objects created in this schema
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL PRIVILEGES ON TABLES TO saas_risk_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL PRIVILEGES ON SEQUENCES TO saas_risk_user;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Schema migrations tracking table
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Record this migration
INSERT INTO schema_migrations (version, name) 
VALUES ('001', 'create_database')
ON CONFLICT (version) DO NOTHING;
