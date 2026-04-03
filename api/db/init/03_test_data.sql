-- ============================================================
-- Data Quality Agent — Seed Rules
-- One rule per known DQ issue in the test data
-- ============================================================

INSERT INTO rules (name, description, category, severity, sql_query, is_active, created_by) VALUES

-- === COMPLETENESS RULES ===

('Missing Base Unit of Measure',
 'Every material must have a base unit of measure (MEINS). Missing MEINS blocks goods movements and order processing.',
 'completeness', 3,
 'SELECT matnr, maktx, meins FROM mara WHERE meins IS NULL AND lvorm IS NULL',
 true, 'seed'),

('Missing Material Group',
 'Material group (MATKL) is required for spend reporting, purchasing automation, and product costing.',
 'completeness', 3,
 'SELECT matnr, maktx, matkl FROM mara WHERE matkl IS NULL AND lvorm IS NULL',
 true, 'seed'),

('Missing Division for Finished Products',
 'Division (SPART) drives sales org determination and profitability reporting. Required for FERT materials.',
 'completeness', 2,
 'SELECT matnr, maktx, mtart, spart FROM mara WHERE spart IS NULL AND mtart = ''FERT'' AND lvorm IS NULL',
 true, 'seed'),

('Missing Product Hierarchy for Finished Products',
 'Product hierarchy (PRDHA) is required for FERT materials for sales planning and reporting.',
 'completeness', 2,
 'SELECT matnr, maktx, mtart, prdha FROM mara WHERE prdha IS NULL AND mtart = ''FERT'' AND lvorm IS NULL',
 true, 'seed'),

('Missing Weight Data for Finished Products',
 'FERT materials shipped to customers must have gross weight, net weight, and weight unit for freight calculation.',
 'completeness', 2,
 'SELECT matnr, maktx, brgew, ntgew, gewei FROM mara WHERE mtart = ''FERT'' AND (brgew IS NULL OR ntgew IS NULL OR gewei IS NULL) AND lvorm IS NULL',
 true, 'seed'),

('Missing Purchasing Group',
 'Materials with external procurement (BESKZ in F, X) must have a purchasing group (EKGRP) for PO routing.',
 'completeness', 3,
 'SELECT mc.matnr, mc.werks, mc.ekgrp, mc.beskz FROM marc mc WHERE mc.ekgrp IS NULL AND mc.beskz IN (''F'', ''X'') AND mc.lvorm IS NULL',
 true, 'seed'),

('Missing MRP Controller',
 'MRP-active materials (DISMM is not null) must have an assigned MRP controller (DISPO) for exception monitoring.',
 'completeness', 3,
 'SELECT mc.matnr, mc.werks, mc.dispo, mc.dismm FROM marc mc WHERE mc.dispo IS NULL AND mc.dismm IS NOT NULL AND mc.lvorm IS NULL',
 true, 'seed'),

('Missing Valuation Class',
 'Valuation class (BKLAS) is required for inventory account determination in FI. Without it, goods receipt fails.',
 'completeness', 3,
 'SELECT mc.matnr, mc.werks, mc.bklas FROM marc mc WHERE mc.bklas IS NULL AND mc.lvorm IS NULL',
 true, 'seed'),

-- === VALIDITY RULES ===

('Invalid Material Type',
 'Material type (MTART) must reference a valid entry in T134. Invalid types cannot be processed by downstream systems.',
 'validity', 3,
 'SELECT m.matnr, m.maktx, m.mtart FROM mara m LEFT JOIN t134 t ON m.mtart = t.mtart WHERE t.mtart IS NULL',
 true, 'seed'),

('Zero Standard Price',
 'Materials with standard price control (VPRSV=S) must have a non-zero standard price (STPRS). Zero price causes all goods movements to post at zero value.',
 'validity', 3,
 'SELECT mc.matnr, mc.werks, mc.vprsv, mc.stprs FROM marc mc WHERE mc.vprsv = ''S'' AND (mc.stprs IS NULL OR mc.stprs = 0) AND mc.lvorm IS NULL',
 true, 'seed'),

-- === CONSISTENCY RULES ===

('In-House Production Missing Production Time',
 'Materials with in-house procurement (BESKZ=E) must have an in-house production time (DZEIT) for production scheduling.',
 'consistency', 3,
 'SELECT mc.matnr, mc.werks, mc.beskz, mc.dzeit FROM marc mc WHERE mc.beskz = ''E'' AND mc.dzeit IS NULL AND mc.lvorm IS NULL',
 true, 'seed'),

-- === UNIQUENESS RULES ===

('Near-Duplicate Material Description',
 'Materials with identical descriptions (ignoring whitespace differences) in the same group/division/hierarchy may be duplicates.',
 'uniqueness', 2,
 'SELECT a.matnr AS matnr_a, b.matnr AS matnr_b, a.maktx AS desc_a, b.maktx AS desc_b FROM mara a JOIN mara b ON a.matnr < b.matnr AND a.matkl = b.matkl AND a.spart = b.spart AND a.prdha = b.prdha WHERE a.matkl IS NOT NULL AND a.spart IS NOT NULL AND a.prdha IS NOT NULL AND LOWER(REPLACE(a.maktx, '' '', '''')) = LOWER(REPLACE(b.maktx, '' '', ''''))',
 true, 'seed'),

-- === REFERENTIAL INTEGRITY RULES ===

('Invalid Plant Reference',
 'MARC records must reference a valid plant in T001W. Orphaned plant extensions indicate configuration errors.',
 'referential_integrity', 3,
 'SELECT mc.matnr, mc.werks FROM marc mc LEFT JOIN t001w t ON mc.werks = t.werks WHERE t.werks IS NULL',
 true, 'seed'),

-- === TIMELINESS RULES ===

('Stale Material Record',
 'Materials not updated in over 3 years may be stale and are candidates for archiving or status review.',
 'timeliness', 1,
 'SELECT matnr, maktx, laeda FROM mara WHERE laeda < CURRENT_DATE - INTERVAL ''3 years'' AND lvorm IS NULL',
 true, 'seed'),

-- === ORPHANS RULES ===

('Plant Extension for Deletion-Flagged Material',
 'Active plant extensions (MARC) exist for materials flagged for deletion at client level (MARA.LVORM=X). These should be cleaned up.',
 'orphans', 2,
 'SELECT mc.matnr, mc.werks, m.lvorm AS mara_lvorm FROM marc mc JOIN mara m ON mc.matnr = m.matnr WHERE m.lvorm = ''X'' AND mc.lvorm IS NULL',
 true, 'seed'),

-- === BUSINESS RULES ===

('Batch-Managed Material Missing Shelf Life',
 'Materials with batch management active (XCHPF=X) must have minimum remaining shelf life (MHDRZ) or total shelf life (MHDLP) configured.',
 'business_rules', 3,
 'SELECT matnr, maktx, xchpf, mhdrz, mhdlp FROM mara WHERE xchpf = ''X'' AND (mhdrz IS NULL AND mhdlp IS NULL)',
 true, 'seed'),

('Client-Level Deletion Flag Set',
 'Materials flagged for deletion at client level (LVORM=X). Verify no open purchase orders or production orders exist.',
 'business_rules', 1,
 'SELECT matnr, maktx, lvorm FROM mara WHERE lvorm = ''X''',
 true, 'seed');
