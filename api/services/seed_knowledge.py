"""Seed knowledge entries on first startup.

Creates foundational SAP/ERP domain knowledge with embeddings so the agent
has useful context from day one. Only runs if the knowledge_entries table is empty.
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.knowledge import KnowledgeEntry
from services.embeddings import generate_embedding

logger = logging.getLogger(__name__)

SEED_ENTRIES = [
    {
        "title": "SAP Material Types (MTART)",
        "content": (
            "Material types control which screens and fields are available during material master maintenance. "
            "Key types in this system: ROH (Raw Materials) — purchased and consumed in production; "
            "HALB (Semifinished Products) — manufactured intermediates; "
            "FERT (Finished Products) — sold to customers, require full sales and logistics data; "
            "HAWA (Trading Goods) — purchased and resold without transformation; "
            "VERP (Packaging Materials); DIEN (Services); NLAG (Non-Stock Materials). "
            "FERT materials have the strictest data requirements because they flow through sales, production, and shipping."
        ),
        "tags": ["sap", "material-master", "reference-data"],
    },
    {
        "title": "SAP Material Master Structure: MARA vs MARC",
        "content": (
            "MARA holds client-level (global) material attributes shared across all plants: description, material type, "
            "material group, weights, units of measure, batch management settings, and deletion flags. "
            "MARC holds plant-level data: procurement type, MRP settings, pricing, purchasing group, storage locations, "
            "and plant-specific status. A single MARA record can have multiple MARC records (one per plant the material "
            "is extended to). Data quality rules must consider both levels — a material can be clean at client level "
            "but have issues at specific plants."
        ),
        "tags": ["sap", "material-master", "data-model"],
    },
    {
        "title": "Base Unit of Measure (MEINS)",
        "content": (
            "The base unit of measure (MEINS) in MARA is the fundamental unit for inventory management. "
            "All stock quantities are tracked in this unit. Common values: EA (each), KG (kilogram), "
            "L (liter), M (meter), PR (pair). A missing MEINS blocks goods receipts, goods issues, "
            "and order processing — it is one of the most critical fields in the material master. "
            "Alternative units of measure can be defined for ordering or sales, but they always convert back to MEINS."
        ),
        "tags": ["sap", "material-master", "completeness"],
    },
    {
        "title": "Procurement Types in SAP (BESKZ)",
        "content": (
            "The procurement type (BESKZ) in MARC determines how a material is sourced: "
            "E = In-house production (manufactured internally, requires production time DZEIT and routing); "
            "F = External procurement (purchased from vendors, requires purchasing group EKGRP and planned delivery time PLIFZ); "
            "X = Both (can be produced or purchased depending on the situation). "
            "Data quality rules should validate that supporting fields match the procurement type — "
            "e.g., BESKZ=E without DZEIT means production cannot be scheduled."
        ),
        "tags": ["sap", "material-master", "procurement", "consistency"],
    },
    {
        "title": "MRP Configuration Fields",
        "content": (
            "Key MRP fields in MARC: DISMM (MRP type) controls planning — PD means MRP-driven, VB means reorder point. "
            "DISPO (MRP controller) is the person responsible for reviewing MRP results and exceptions. "
            "DISLS (lot sizing) determines order quantity calculation: EX (lot-for-lot), FX (fixed lot size). "
            "MINBE (reorder point) and EISBE (safety stock) are critical for VB-type materials. "
            "PLIFZ (planned delivery time) is used for scheduling external procurement. "
            "Missing or inconsistent MRP fields cause planning failures and stock-outs."
        ),
        "tags": ["sap", "material-master", "mrp", "planning"],
    },
    {
        "title": "Price Control in SAP (VPRSV)",
        "content": (
            "VPRSV in MARC determines how inventory is valued: "
            "S = Standard price (STPRS) — price is fixed and variances are posted to price difference accounts. "
            "V = Moving average price (VERPR) — price adjusts with each goods receipt. "
            "A zero standard price (VPRSV=S with STPRS=0) is a serious error: all goods movements post at zero value, "
            "distorting inventory valuation and cost of goods sold. BKLAS (valuation class) determines which "
            "G/L accounts are posted to — a missing valuation class blocks goods receipt entirely."
        ),
        "tags": ["sap", "material-master", "finance", "valuation"],
    },
    {
        "title": "Material Deletion Flags (LVORM)",
        "content": (
            "LVORM is the deletion flag. In MARA, it flags the material for deletion across all plants (client-level). "
            "In MARC, it flags the material at a specific plant only. When MARA.LVORM='X', all MARC records should "
            "also be flagged or cleaned up — active plant extensions for deletion-flagged materials are orphaned data. "
            "Before deletion, verify: no open purchase orders, no open production orders, no warehouse stock, "
            "and no pending deliveries. Materials with LVORM='X' should generally be excluded from data quality checks "
            "for active data issues (completeness, validity) since they are being retired."
        ),
        "tags": ["sap", "material-master", "lifecycle", "deletion"],
    },
    {
        "title": "Batch Management and Shelf Life",
        "content": (
            "When XCHPF='X' in MARA, batch management is active — the material is tracked in discrete batches "
            "with unique batch numbers. This is common for chemicals, pharmaceuticals, and food products. "
            "Batch-managed materials typically require shelf life data: MHDRZ (minimum remaining shelf life in days) "
            "controls whether a batch can be issued based on its remaining life; MHDLP (total shelf life in days) "
            "defines the batch's total lifespan from production date. Missing shelf life on a batch-managed material "
            "means expired stock cannot be detected automatically."
        ),
        "tags": ["sap", "material-master", "batch", "shelf-life", "business-rules"],
    },
    {
        "title": "Material Group (MATKL) and Product Hierarchy (PRDHA)",
        "content": (
            "MATKL (material group) in MARA classifies materials for reporting and purchasing: "
            "it drives spend analysis, automatic source determination, and product costing allocations. "
            "PRDHA (product hierarchy) is a multi-level classification primarily used for sales reporting and planning. "
            "FERT materials especially need both: MATKL for procurement reporting, PRDHA for sales analytics. "
            "These must reference valid entries in their respective reference tables (T023 for MATKL). "
            "Missing or incorrect classification leads to materials being excluded from reports and automation."
        ),
        "tags": ["sap", "material-master", "classification", "reporting"],
    },
    {
        "title": "Data Quality Rule Categories",
        "content": (
            "Rules in this system are categorized as: "
            "completeness — required fields that are missing (e.g., no MEINS, no EKGRP); "
            "validity — values that exist but are invalid (e.g., MTART not in T134); "
            "consistency — fields that contradict each other (e.g., BESKZ=E but no DZEIT); "
            "uniqueness — potential duplicate records (e.g., near-identical descriptions in same group); "
            "referential_integrity — foreign key violations (e.g., MARC.WERKS not in T001W); "
            "timeliness — records that may be stale (e.g., not updated in 3+ years); "
            "orphans — records that should have been cleaned up (e.g., active MARC for deleted MARA); "
            "business_rules — domain-specific validations (e.g., batch-managed material without shelf life)."
        ),
        "tags": ["data-quality", "rules", "categories"],
    },
]


async def seed_knowledge_entries(session: AsyncSession) -> None:
    """Insert seed knowledge entries if the table is empty."""
    result = await session.execute(
        select(func.count()).select_from(KnowledgeEntry)
    )
    count = result.scalar()

    if count > 0:
        logger.info(f"Knowledge base already has {count} entries, skipping seed.")
        return

    logger.info(f"Seeding {len(SEED_ENTRIES)} knowledge entries with embeddings...")

    for entry_data in SEED_ENTRIES:
        text_for_embedding = f"{entry_data['title']} {entry_data['content']}"
        embedding = await generate_embedding(text_for_embedding)

        entry = KnowledgeEntry(
            title=entry_data["title"],
            content=entry_data["content"],
            source_type="analyst",
            tags=entry_data["tags"],
            embedding=embedding,
        )
        session.add(entry)

    await session.commit()
    logger.info("Knowledge base seeded successfully.")
