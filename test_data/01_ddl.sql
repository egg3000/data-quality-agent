-- ============================================================
-- Data Quality Agent — Test Data DDL
-- SAP Material Master Domain
--
-- Tables created:
--   t001w  — Plants reference (SAP T001W)
--   t134   — Material Types reference (SAP T134)
--   t023   — Material Groups reference (SAP T023)
--   mara   — General Material Data, client level (SAP MARA)
--   marc   — Plant Data for Material, plant level (SAP MARC)
--
-- Run this file first, then 02_seed_data.sql
-- ============================================================


-- -------------------------------------------------------
-- Reference: Plants (SAP T001W equivalent)
-- -------------------------------------------------------
DROP TABLE IF EXISTS t001w CASCADE;
CREATE TABLE t001w (
    werks   VARCHAR(4)   PRIMARY KEY,
    name1   VARCHAR(30)  NOT NULL,       -- Plant Name
    land1   VARCHAR(3),                  -- Country Key
    regio   VARCHAR(3)                   -- Region / State
);


-- -------------------------------------------------------
-- Reference: Valid Material Types (SAP T134 equivalent)
-- -------------------------------------------------------
DROP TABLE IF EXISTS t134 CASCADE;
CREATE TABLE t134 (
    mtart   VARCHAR(4)   PRIMARY KEY,
    mtbez   VARCHAR(25)  NOT NULL        -- Material Type Description
);


-- -------------------------------------------------------
-- Reference: Material Groups (SAP T023 equivalent)
-- -------------------------------------------------------
DROP TABLE IF EXISTS t023 CASCADE;
CREATE TABLE t023 (
    matkl   VARCHAR(9)   PRIMARY KEY,
    wgbez   VARCHAR(40)  NOT NULL        -- Material Group Description
);


-- -------------------------------------------------------
-- MARA: General Material Data (Client Level)
-- One row per material number — attributes shared across all plants
-- -------------------------------------------------------
DROP TABLE IF EXISTS mara CASCADE;
CREATE TABLE mara (
    matnr   VARCHAR(18)  PRIMARY KEY,    -- Material Number
    ersda   DATE,                        -- Creation Date
    ernam   VARCHAR(12),                 -- Created By (user ID)
    laeda   DATE,                        -- Date of Last Change
    aenam   VARCHAR(12),                 -- Changed By (user ID)
    mtart   VARCHAR(4),                  -- Material Type (FK → t134)
    mbrsh   CHAR(1),                     -- Industry Sector: M=Mech Eng, A=Plant Maint, D=Pharma
    matkl   VARCHAR(9),                  -- Material Group (FK → t023)
    maktx   VARCHAR(40),                 -- Short Description (normally in MAKT; included here for simplicity)
    meins   VARCHAR(3),                  -- Base Unit of Measure
    brgew   NUMERIC(13,3),               -- Gross Weight
    ntgew   NUMERIC(13,3),               -- Net Weight
    gewei   VARCHAR(3),                  -- Weight Unit
    volum   NUMERIC(13,3),               -- Volume
    voleh   VARCHAR(3),                  -- Volume Unit
    spart   VARCHAR(2),                  -- Division
    prdha   VARCHAR(18),                 -- Product Hierarchy
    bismt   VARCHAR(18),                 -- Old / Supplier Material Number
    mhdrz   SMALLINT,                    -- Minimum Remaining Shelf Life (days)
    mhdlp   SMALLINT,                    -- Total Shelf Life (days)
    xchpf   CHAR(1),                     -- Batch Management Indicator (X = required)
    mstae   VARCHAR(2),                  -- Cross-Plant Material Status
    mstdv   DATE,                        -- Cross-Plant Status Valid From
    lvorm   CHAR(1)                      -- Client-Level Deletion Flag (X = flagged)
);


-- -------------------------------------------------------
-- MARC: Plant Data for Material (Plant Level)
-- One row per material+plant combination
-- -------------------------------------------------------
DROP TABLE IF EXISTS marc CASCADE;
CREATE TABLE marc (
    matnr   VARCHAR(18)  NOT NULL,       -- Material Number (FK → mara)
    werks   VARCHAR(4)   NOT NULL,       -- Plant (FK → t001w)
    PRIMARY KEY (matnr, werks),

    pstat   VARCHAR(15),                 -- Maintenance Status Flags
    lvorm   CHAR(1),                     -- Plant-Level Deletion Flag (X = flagged)
    beskz   CHAR(1),                     -- Procurement Type: E=In-house, F=External, X=Both
    sobsl   VARCHAR(2),                  -- Special Procurement Type
    minbe   NUMERIC(13,3),               -- Reorder Point
    eisbe   NUMERIC(13,3),               -- Safety Stock
    mabst   NUMERIC(13,3),               -- Maximum Stock Level
    webaz   SMALLINT,                    -- Goods Receipt Processing Time (workdays)
    plifz   SMALLINT,                    -- Planned Delivery Time (days)
    dzeit   SMALLINT,                    -- In-house Production Time (days)
    ekgrp   VARCHAR(3),                  -- Purchasing Group
    dismm   VARCHAR(2),                  -- MRP Type (e.g. PD=MRP, VB=Reorder Point)
    dispo   VARCHAR(3),                  -- MRP Controller
    disls   VARCHAR(2),                  -- Lot Sizing Procedure
    mtvfp   VARCHAR(2),                  -- Availability Check Rule
    vprsv   CHAR(1),                     -- Price Control: S=Standard Price, V=Moving Avg
    verpr   NUMERIC(13,3),               -- Moving Average Price / Periodic Unit Price
    stprs   NUMERIC(13,3),               -- Standard Price
    peinh   NUMERIC(5,0),                -- Price Unit
    bklas   VARCHAR(4),                  -- Valuation Class
    ausme   VARCHAR(3),                  -- Unit of Issue
    lgpro   VARCHAR(4),                  -- Issue Storage Location
    lgfsb   VARCHAR(4),                  -- Storage Location for External Procurement
    rgekz   CHAR(1),                     -- Post to Inspection Stock Indicator
    mstae   VARCHAR(2),                  -- Plant-Specific Material Status
    mstdv   DATE                         -- Plant Status Valid From
);
