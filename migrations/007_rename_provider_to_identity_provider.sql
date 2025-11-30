-- Migration: 007_rename_provider_to_identity_provider
-- Description: Rename provider tables and columns to identity_provider for clarity
-- Created: 2025-11-30

-- ============================================
-- STEP 1: Rename the provider table to identity_provider
-- ============================================
ALTER TABLE provider RENAME TO identity_provider;

-- Rename the constraint
ALTER TABLE identity_provider 
    RENAME CONSTRAINT uq_provider_slug TO uq_identity_provider_slug;

-- ============================================
-- STEP 2: Rename org_provider_connection table
-- ============================================
ALTER TABLE org_provider_connection RENAME TO identity_provider_connection;

-- Rename the column provider_id to identity_provider_id
ALTER TABLE identity_provider_connection 
    RENAME COLUMN provider_id TO identity_provider_id;

-- Rename constraints
ALTER TABLE identity_provider_connection 
    RENAME CONSTRAINT uq_org_provider_conn_org_provider TO uq_identity_provider_conn_org_provider;

-- Rename indexes
ALTER INDEX idx_org_provider_conn_org RENAME TO idx_identity_provider_conn_org;
ALTER INDEX idx_org_provider_conn_provider RENAME TO idx_identity_provider_conn_identity_provider;
ALTER INDEX idx_org_provider_conn_status RENAME TO idx_identity_provider_conn_status;
ALTER INDEX idx_org_provider_conn_connected_by RENAME TO idx_identity_provider_conn_connected_by;

-- ============================================
-- STEP 3: Update foreign key references in other tables
-- ============================================

-- Update product table: rename provider_id to identity_provider_id
ALTER TABLE product 
    RENAME COLUMN provider_id TO identity_provider_id;

ALTER INDEX idx_product_provider RENAME TO idx_product_identity_provider;

-- Update product_auth_config table: rename provider_id to identity_provider_id
ALTER TABLE product_auth_config 
    RENAME COLUMN provider_id TO identity_provider_id;

-- ============================================
-- Record this migration
-- ============================================
INSERT INTO schema_migrations (version, name) 
VALUES ('007', 'rename_provider_to_identity_provider')
ON CONFLICT (version) DO NOTHING;
