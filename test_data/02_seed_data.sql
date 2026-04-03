-- ============================================================
-- Data Quality Agent — Test Seed Data
-- SAP Material Master Domain (MARA + MARC)
--
-- Records are a mix of clean data and intentionally dirty data.
-- Dirty records are annotated with [DQ-ISSUE] comments
-- indicating the category and nature of the problem.
-- These issues are the targets for the first set of DQ rules.
--
-- Run 01_ddl.sql before this file.
-- ============================================================


-- -------------------------------------------------------
-- Reference Data
-- -------------------------------------------------------

INSERT INTO t001w (werks, name1, land1, regio) VALUES
    ('1000', 'Main Manufacturing Plant',  'US', 'OH'),
    ('1100', 'Secondary Assembly Plant',  'US', 'MI'),
    ('2000', 'Distribution Center East',  'US', 'PA');

INSERT INTO t134 (mtart, mtbez) VALUES
    ('ROH',  'Raw Materials'),
    ('HALB', 'Semifinished Products'),
    ('FERT', 'Finished Products'),
    ('HAWA', 'Trading Goods'),
    ('DIEN', 'Services'),
    ('VERP', 'Packaging Materials'),
    ('NLAG', 'Non-Stock Materials');

INSERT INTO t023 (matkl, wgbez) VALUES
    ('PUMP-ASSY',  'Pump Assemblies'),
    ('MOTORS',     'Electric Motors'),
    ('STEEL-RAW',  'Steel Raw Materials'),
    ('COPR-RAW',  'Copper Raw Materials'),
    ('PUMP-COMP',  'Pump Components'),
    ('PPE-ITEMS',  'PPE & Safety Items'),
    ('PACKAGING',  'Packaging Materials'),
    ('CHEM-RAW',   'Chemical Raw Materials');


-- -------------------------------------------------------
-- MARA: General Material Data
-- -------------------------------------------------------

INSERT INTO mara (
    matnr,       ersda,        ernam,      laeda,        aenam,
    mtart, mbrsh, matkl,       maktx,
    meins, brgew,  ntgew,  gewei, volum,  voleh,
    spart, prdha,           bismt,
    mhdrz, mhdlp, xchpf, mstae, mstdv, lvorm
) VALUES

-- === CLEAN RECORDS ===

('MAT-000001', '2022-01-15', 'JSMITH',    '2024-03-10', 'JSMITH',
 'FERT', 'M', 'PUMP-ASSY',  'Industrial Pump Assembly 50Hz',
 'EA',  45.500, 42.000, 'KG', 28.000, 'L',
 '01', 'A000100010001', NULL,
 NULL, NULL, NULL, NULL, NULL, NULL),

('MAT-000002', '2022-01-15', 'JSMITH',    '2024-01-05', 'BWILSON',
 'FERT', 'M', 'MOTORS',     'Electric Motor 5kW 3-Phase',
 'EA',  22.000, 20.500, 'KG', 12.000, 'L',
 '01', 'A000100020001', NULL,
 NULL, NULL, NULL, NULL, NULL, NULL),

('MAT-000003', '2021-06-01', 'LGARCIA',   '2023-11-20', 'LGARCIA',
 'ROH',  'M', 'STEEL-RAW',  'Steel Rod 20mm x 6m',
 'KG',   1.000,  1.000, 'KG', NULL,   NULL,
 '02', 'B000200010001', NULL,
 NULL, NULL, NULL, NULL, NULL, NULL),

('MAT-000004', '2021-06-01', 'LGARCIA',   '2023-11-20', 'LGARCIA',
 'ROH',  'M', 'COPR-RAW',  'Copper Wire 2.5mm Roll 100m',
 'KG',   1.000,  1.000, 'KG', NULL,   NULL,
 '02', 'B000200020001', NULL,
 NULL, NULL, NULL, NULL, NULL, NULL),

('MAT-000005', '2022-03-10', 'RWILLIAMS', '2024-02-14', 'RWILLIAMS',
 'HALB', 'M', 'PUMP-COMP',  'Pump Housing Casting Type A',
 'EA',  18.000, 16.500, 'KG', 10.000, 'L',
 '01', 'A000100030001', NULL,
 NULL, NULL, NULL, NULL, NULL, NULL),

('MAT-000006', '2020-09-15', 'MCHEN',     '2022-06-01', 'MCHEN',
 'HAWA', 'A', 'PPE-ITEMS',  'Safety Gloves Cut-Resistant XL',
 'PR',   0.300,  0.250, 'KG', NULL,   NULL,
 '03', 'C000300010001', NULL,
 NULL, NULL, NULL, NULL, NULL, NULL),

('MAT-000007', '2020-09-15', 'MCHEN',     '2023-04-10', 'MCHEN',
 'VERP', 'M', 'PACKAGING',  'Cardboard Box 500x400x300mm',
 'EA',   0.800,  0.750, 'KG', 60.000, 'L',
 '04', 'D000400010001', NULL,
 NULL, NULL, NULL, NULL, NULL, NULL),


-- === DIRTY RECORDS ===

-- [DQ-ISSUE: COMPLETENESS] Missing base unit of measure (MEINS = NULL)
-- Every material must have a base UOM — this breaks downstream order and inventory processing
('MAT-000008', '2023-05-12', 'TMORGAN',   '2023-05-12', 'TMORGAN',
 'FERT', 'M', 'PUMP-ASSY',  'Centrifugal Pump 75Hz',
 NULL,  30.000, 28.000, 'KG', 15.000, 'L',
 '01', 'A000100010002', NULL,
 NULL, NULL, NULL, NULL, NULL, NULL),

-- [DQ-ISSUE: COMPLETENESS] Missing material group (MATKL = NULL)
-- Required for spend reporting, purchasing automation, and product costing
('MAT-000009', '2023-06-20', 'TMORGAN',   '2023-06-20', 'TMORGAN',
 'FERT', 'M', NULL,         'Inline Pump Assembly 60Hz',
 'EA',  25.000, 23.000, 'KG', 14.000, 'L',
 '01', 'A000100010003', NULL,
 NULL, NULL, NULL, NULL, NULL, NULL),

-- [DQ-ISSUE: COMPLETENESS] Missing division (SPART = NULL)
-- Division drives sales org determination and profitability reporting
('MAT-000010', '2023-07-01', 'JSMITH',    '2023-07-01', 'JSMITH',
 'FERT', 'M', 'PUMP-ASSY',  'Booster Pump Assembly 50Hz',
 'EA',  44.000, 41.000, 'KG', 27.000, 'L',
 NULL,  'A000100010004', NULL,
 NULL, NULL, NULL, NULL, NULL, NULL),

-- [DQ-ISSUE: COMPLETENESS] Missing product hierarchy (PRDHA = NULL)
-- FERT materials require product hierarchy for sales planning and reporting
('MAT-000011', '2023-07-15', 'JSMITH',    '2023-07-15', 'JSMITH',
 'FERT', 'M', 'PUMP-ASSY',  'Submersible Pump 1.5kW',
 'EA',  38.000, 35.000, 'KG', 22.000, 'L',
 '01',  NULL,            NULL,
 NULL, NULL, NULL, NULL, NULL, NULL),

-- [DQ-ISSUE: COMPLETENESS] Missing all weight data (BRGEW/NTGEW/GEWEI = NULL)
-- FERT materials shipped to customers must have weight for freight calculation
('MAT-000012', '2023-08-10', 'BWILSON',   '2023-08-10', 'BWILSON',
 'FERT', 'M', 'MOTORS',     'Electric Motor 7.5kW 3-Phase',
 'EA',   NULL,  NULL,  NULL,  NULL,  NULL,
 '01', 'A000100020002', NULL,
 NULL, NULL, NULL, NULL, NULL, NULL),

-- [DQ-ISSUE: VALIDITY] Invalid material type — ZZZZ does not exist in T134
-- This record cannot be properly processed by SAP or downstream systems
('MAT-000013', '2023-09-01', 'LGARCIA',   '2023-09-01', 'LGARCIA',
 'ZZZZ', 'M', 'STEEL-RAW',  'Steel Plate 10mm x 2000x1000',
 'KG',   1.000,  1.000, 'KG', NULL,   NULL,
 '02', 'B000200010002', NULL,
 NULL, NULL, NULL, NULL, NULL, NULL),

-- [DQ-ISSUE: TIMELINESS] Last changed over 3 years ago — record may be stale
-- Materials inactive this long are candidates for archiving or status review
('MAT-000014', '2019-01-10', 'FORMER01',  '2020-11-30', 'FORMER01',
 'ROH',  'M', 'STEEL-RAW',  'Steel Angle Bar 50x50x5mm',
 'KG',   1.000,  1.000, 'KG', NULL,   NULL,
 '02', 'B000200010003', NULL,
 NULL, NULL, NULL, NULL, NULL, NULL),

-- [DQ-ISSUE: UNIQUENESS] Description nearly identical to MAT-000001 — potential duplicate
-- Same material group, same division, same product hierarchy, similar weight
('MAT-000015', '2024-01-08', 'TMORGAN',   '2024-01-08', 'TMORGAN',
 'FERT', 'M', 'PUMP-ASSY',  'Industrial Pump Assembly 50 Hz',
 'EA',  45.600, 42.100, 'KG', 28.100, 'L',
 '01', 'A000100010001', NULL,
 NULL, NULL, NULL, NULL, NULL, NULL),

-- [DQ-ISSUE: COMPLETENESS] Batch-managed material with no shelf life configured
-- XCHPF='X' means batch management is active — MHDRZ and MHDLP are then required
('MAT-000016', '2023-10-05', 'DPARK',     '2023-10-05', 'DPARK',
 'ROH',  'D', 'CHEM-RAW',   'Chemical Compound XR-200',
 'KG',   5.000,  5.000, 'KG', NULL,   NULL,
 '05', 'E000500010001', NULL,
 NULL, NULL, 'X', NULL, NULL, NULL),

-- [DQ-ISSUE: BUSINESS RULES] Deletion flag set at client level
-- Flagged materials should have no open purchase orders or production orders
('MAT-000017', '2021-03-20', 'JSMITH',    '2023-01-15', 'JSMITH',
 'FERT', 'M', 'PUMP-ASSY',  'Obsolete Pump Assembly V1',
 'EA',  20.000, 18.500, 'KG', 11.000, 'L',
 '01', 'A000100010001', NULL,
 NULL, NULL, NULL, NULL, NULL, 'X');


-- -------------------------------------------------------
-- MARC: Plant Data for Material
-- -------------------------------------------------------

INSERT INTO marc (
    matnr,       werks,
    pstat, lvorm, beskz, sobsl,
    minbe, eisbe, mabst, webaz, plifz, dzeit,
    ekgrp, dismm, dispo, disls, mtvfp,
    vprsv, verpr,  stprs,  peinh, bklas,
    ausme, lgpro, lgfsb, rgekz, mstae, mstdv
) VALUES

-- === CLEAN RECORDS ===

-- MAT-000001 at Plant 1000: Finished good, in-house production, standard price
('MAT-000001', '1000',
 'EGPVX', NULL, 'E', NULL,
 5.000, 2.000, 50.000, 1, 30, 15,
 'P01', 'PD', 'M01', 'EX', '02',
 'S', NULL, 1250.00, 1, '7920',
 'EA', '0001', NULL, NULL, NULL, NULL),

-- MAT-000001 at Plant 1100: Same material, second plant
('MAT-000001', '1100',
 'EGPVX', NULL, 'E', NULL,
 3.000, 1.000, 30.000, 1, 30, 15,
 'P01', 'PD', 'M02', 'EX', '02',
 'S', NULL, 1250.00, 1, '7920',
 'EA', '0001', NULL, NULL, NULL, NULL),

-- MAT-000002 at Plant 1000: Finished good, in-house production, standard price
('MAT-000002', '1000',
 'EGPVX', NULL, 'E', NULL,
 10.000, 5.000, 100.000, 1, 45, 20,
 'P01', 'PD', 'M01', 'EX', '02',
 'S', NULL, 875.00, 1, '7920',
 'EA', '0001', NULL, NULL, NULL, NULL),

-- MAT-000003 at Plant 1000: Raw material, external procurement, moving average price
('MAT-000003', '1000',
 'EBP', NULL, 'F', NULL,
 500.000, 200.000, 5000.000, 2, 14, NULL,
 'P02', 'PD', 'M03', 'EX', '02',
 'V', 3.850, NULL, 1, '3000',
 'KG', '0002', '0002', NULL, NULL, NULL),

-- MAT-000004 at Plant 1000: Raw material, external procurement, moving average price
('MAT-000004', '1000',
 'EBP', NULL, 'F', NULL,
 100.000, 50.000, 1000.000, 2, 21, NULL,
 'P02', 'PD', 'M03', 'EX', '02',
 'V', 12.400, NULL, 1, '3000',
 'KG', '0002', '0002', NULL, NULL, NULL),

-- MAT-000005 at Plant 1000: Semi-finished, both procurement types
('MAT-000005', '1000',
 'EGBP', NULL, 'X', NULL,
 20.000, 10.000, 200.000, 1, 21, 10,
 'P01', 'PD', 'M01', 'EX', '02',
 'S', NULL, 320.00, 1, '7910',
 'EA', '0001', '0002', NULL, NULL, NULL),

-- MAT-000006 at Plant 2000: Trading good, external procurement, moving average
('MAT-000006', '2000',
 'EBP', NULL, 'F', NULL,
 50.000, 20.000, 500.000, 1, 7, NULL,
 'P03', 'VB', 'M04', 'FX', '02',
 'V', 8.750, NULL, 1, '3100',
 'PR', '0003', '0003', NULL, NULL, NULL),

-- MAT-000007 at Plant 1000: Packaging, external procurement
('MAT-000007', '1000',
 'EBP', NULL, 'F', NULL,
 200.000, 100.000, 2000.000, 1, 7, NULL,
 'P02', 'VB', 'M03', 'FX', '02',
 'V', 0.920, NULL, 1, '3200',
 'EA', '0002', '0002', NULL, NULL, NULL),


-- === DIRTY RECORDS ===

-- [DQ-ISSUE: COMPLETENESS] MAT-000008 at Plant 1000: Missing purchasing group (EKGRP = NULL)
-- External procurement materials must have a purchasing group for PO routing
('MAT-000008', '1000',
 'EBP', NULL, 'F', NULL,
 10.000, 5.000, 100.000, 2, 30, NULL,
 NULL,  'PD', 'M03', 'EX', '02',
 'S', NULL, 950.00, 1, '7920',
 'EA', '0001', '0001', NULL, NULL, NULL),

-- [DQ-ISSUE: COMPLETENESS] MAT-000009 at Plant 1000: Missing MRP controller (DISPO = NULL)
-- MRP-active materials must have an assigned controller for exception monitoring
('MAT-000009', '1000',
 'EGP', NULL, 'E', NULL,
 5.000, 2.000, 50.000, 1, 30, 15,
 'P01', 'PD', NULL,  'EX', '02',
 'S', NULL, 1100.00, 1, '7920',
 'EA', '0001', NULL, NULL, NULL, NULL),

-- [DQ-ISSUE: COMPLETENESS] MAT-000010 at Plant 1000: Missing valuation class (BKLAS = NULL)
-- Required for inventory account determination in FI — material cannot be goods receipted
('MAT-000010', '1000',
 'EGP', NULL, 'E', NULL,
 5.000, 2.000, 50.000, 1, 30, 15,
 'P01', 'PD', 'M01', 'EX', '02',
 'S', NULL, 980.00, 1, NULL,
 'EA', '0001', NULL, NULL, NULL, NULL),

-- [DQ-ISSUE: VALIDITY] MAT-000012 at Plant 1000: Standard price control (VPRSV='S') but STPRS = 0
-- A zero standard price causes all goods movements to post at zero value — serious costing error
('MAT-000012', '1000',
 'EGP', NULL, 'E', NULL,
 5.000, 2.000, 50.000, 1, 45, 20,
 'P01', 'PD', 'M01', 'EX', '02',
 'S', NULL, 0.000, 1, '7920',
 'EA', '0001', NULL, NULL, NULL, NULL),

-- [DQ-ISSUE: REFERENTIAL INTEGRITY] MAT-000014 at Plant 9999: Plant does not exist in T001W
-- MARC record extended to a non-existent plant — orphaned configuration
('MAT-000014', '9999',
 'EBP', NULL, 'F', NULL,
 100.000, 50.000, 1000.000, 2, 14, NULL,
 'P02', 'PD', 'M03', 'EX', '02',
 'V', 2.100, NULL, 1, '3000',
 'KG', '0002', '0002', NULL, NULL, NULL),

-- [DQ-ISSUE: ORPHANS] MAT-000017 at Plant 1000: Plant extension for a client-deletion-flagged material
-- MARA.LVORM = 'X' — plant data should also be flagged or cleaned up
('MAT-000017', '1000',
 'EGP', NULL, 'E', NULL,
 5.000, 2.000, 50.000, 1, 30, 15,
 'P01', 'PD', 'M01', 'EX', '02',
 'S', NULL, 420.00, 1, '7920',
 'EA', '0001', NULL, NULL, NULL, NULL),

-- [DQ-ISSUE: CONSISTENCY] MAT-000016 at Plant 1000: BESKZ='E' (in-house) but DZEIT = NULL
-- In-house production materials must have an in-house production time for scheduling
('MAT-000016', '1000',
 'EGP', NULL, 'E', NULL,
 10.000, 5.000, 100.000, 1, NULL, NULL,
 'P01', 'PD', 'M03', 'EX', '02',
 'V', 18.500, NULL, 1, '3000',
 'KG', '0001', NULL, NULL, NULL, NULL);
