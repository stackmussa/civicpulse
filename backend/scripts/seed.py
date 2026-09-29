"""Idempotent seed script — populates ≥ 30 realistic complaints.

Running this script twice must not duplicate rows.
Uses deterministic UUIDv5 from complaint text so ON CONFLICT DO NOTHING works.
"""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# UUID namespace for deterministic seed IDs
_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

SEED_DATA = [
    # Water (6 complaints)
    {
        "text": "Water not coming in street 4 since fajr, tankers also not available, please send supply immediately",
        "location": "Street 4, G-9/2, Islamabad",
        "category": "water",
        "priority": "high",
        "summary": "URGENT: No water supply since morning in G-9",
    },
    {
        "text": "Burst water main flooding Street 12 since fajr, water entering ground floors of houses",
        "location": "Street 12, I-8/3, Islamabad",
        "category": "water",
        "priority": "high",
        "summary": "URGENT: Burst main flooding residential street",
    },
    {
        "text": "Pani ka pressure bahut kam hai, second floor tak nahi aa raha since 3 days",
        "location": "Block C, Johar Town, Lahore",
        "category": "water",
        "priority": "normal",
        "summary": "Low water pressure not reaching upper floors",
    },
    {
        "text": "Sewage water overflow from manhole near school entrance, children getting sick",
        "location": "Near Model School, Gulberg, Lahore",
        "category": "water",
        "priority": "high",
        "summary": "URGENT: Sewage overflow near school entrance",
    },
    {
        "text": "Water supply timing is irregular, sometimes comes at 2am only for 30 minutes",
        "location": "Sector F-6, Islamabad",
        "category": "water",
        "priority": "normal",
        "summary": "Irregular water supply schedule",
    },
    {
        "text": "Gutter nala overflowing since last rain, bad smell coming, mosquitoes breeding",
        "location": "Mohalla Shah Faisal, Rawalpindi",
        "category": "water",
        "priority": "normal",
        "summary": "Drain overflow causing health concerns",
    },
    # Electricity (5 complaints)
    {
        "text": "Transformer spark in G-9 market area, very dangerous, children playing nearby",
        "location": "G-9 Markaz, Islamabad",
        "category": "electricity",
        "priority": "high",
        "summary": "URGENT: Sparking transformer near market",
    },
    {
        "text": "Bijli ka wire gir gaya hai road pe, bahut khatarnak situation hai, please fix urgently",
        "location": "Street 7, Satellite Town, Rawalpindi",
        "category": "electricity",
        "priority": "high",
        "summary": "URGENT: Downed power line on road",
    },
    {
        "text": "Load shedding going on for 14 hours daily in our area, meter says we have connection",
        "location": "Block D, North Nazimabad, Karachi",
        "category": "electricity",
        "priority": "normal",
        "summary": "Extended load shedding in residential area",
    },
    {
        "text": "Street light pole is tilting dangerously after last storm, may fall on parked cars",
        "location": "Main Boulevard, DHA Phase 5, Lahore",
        "category": "electricity",
        "priority": "high",
        "summary": "URGENT: Tilting electrical pole after storm",
    },
    {
        "text": "Voltage fluctuation damaging our appliances, AC compressor burned twice this month",
        "location": "Sector I-10/4, Islamabad",
        "category": "electricity",
        "priority": "normal",
        "summary": "Voltage fluctuations damaging household appliances",
    },
    # Sanitation (5 complaints)
    {
        "text": "Kachra pickup nahi ho raha 2 weeks se, pile of garbage near park entrance, rats seen",
        "location": "Park Road, F-8/1, Islamabad",
        "category": "sanitation",
        "priority": "normal",
        "summary": "Garbage not collected for 2 weeks near park",
    },
    {
        "text": "Dustbin overflow on main road, waste spreading everywhere, very dirty and unhygienic",
        "location": "Murree Road, Rawalpindi",
        "category": "sanitation",
        "priority": "normal",
        "summary": "Overflowing dustbins on main road",
    },
    {
        "text": "Safai wala has not come for one month to our street, paying tax but no service",
        "location": "Street 15, Wah Cantt",
        "category": "sanitation",
        "priority": "low",
        "summary": "No sweeper service for one month",
    },
    {
        "text": "Dead animal smell coming from vacant plot, garbage dumped there illegally by restaurants",
        "location": "Near Food Street, Gawalmandi, Lahore",
        "category": "sanitation",
        "priority": "high",
        "summary": "URGENT: Dead animal and illegal dump site",
    },
    {
        "text": "Hospital waste being dumped in residential area drain, medical syringes visible",
        "location": "Near Civil Hospital, Hyderabad",
        "category": "sanitation",
        "priority": "high",
        "summary": "URGENT: Medical waste in residential drain",
    },
    # Roads (5 complaints)
    {
        "text": "Big pothole on main road causing accidents, my motorcycle fell in it last night",
        "location": "GT Road near Gujar Khan",
        "category": "roads",
        "priority": "high",
        "summary": "URGENT: Dangerous pothole causing accidents",
    },
    {
        "text": "Road construction started 6 months ago and left incomplete, dust everywhere daily",
        "location": "Link Road, Bahria Town, Rawalpindi",
        "category": "roads",
        "priority": "normal",
        "summary": "Abandoned road construction causing dust",
    },
    {
        "text": "Footpath tiles broken and uneven, elderly people tripping regularly on the way to mosque",
        "location": "Near Faisal Mosque, E-7, Islamabad",
        "category": "roads",
        "priority": "normal",
        "summary": "Broken footpath tiles near mosque",
    },
    {
        "text": "Speed breaker is too high, bottom of every car scraping, ambulance also gets stuck",
        "location": "Street 3, G-10/2, Islamabad",
        "category": "roads",
        "priority": "normal",
        "summary": "Oversized speed breaker blocking traffic",
    },
    {
        "text": "Rain water collecting on road since months, no drainage system working in the area",
        "location": "Korangi Industrial Area, Karachi",
        "category": "roads",
        "priority": "normal",
        "summary": "Standing rain water due to failed drainage",
    },
    # Streetlights (5 complaints)
    {
        "text": "All streetlights on our road not working since 2 weeks, very dark at night, robbery happened",
        "location": "Street 8, F-11/1, Islamabad",
        "category": "streetlights",
        "priority": "high",
        "summary": "URGENT: No streetlights, robbery reported",
    },
    {
        "text": "Streetlight bulb broken and flickering, sparks coming at night, dangerous for children",
        "location": "Near Government School, Abbottabad",
        "category": "streetlights",
        "priority": "high",
        "summary": "URGENT: Sparking streetlight near school",
    },
    {
        "text": "New colony has no street lights installed at all, residents using torch to walk at night",
        "location": "New City Phase 2, Wah Cantt",
        "category": "streetlights",
        "priority": "normal",
        "summary": "No streetlights installed in new colony",
    },
    {
        "text": "Streetlight staying on during daytime also, waste of electricity, reported 3 times already",
        "location": "Jinnah Avenue, Blue Area, Islamabad",
        "category": "streetlights",
        "priority": "low",
        "summary": "Streetlight running 24/7 wasting electricity",
    },
    {
        "text": "Light pole paint peeling and rusted, looks like it will fall soon during next storm",
        "location": "Chaklala Scheme, Rawalpindi",
        "category": "streetlights",
        "priority": "normal",
        "summary": "Rusted streetlight pole needs replacement",
    },
    # Other (4 complaints)
    {
        "text": "Stray dogs gathering near children park in evening, attacked one child last week",
        "location": "F-7 Markaz Park, Islamabad",
        "category": "other",
        "priority": "high",
        "summary": "URGENT: Stray dogs attacking children near park",
    },
    {
        "text": "Loud construction noise from 11pm to 5am daily near residential area, cannot sleep",
        "location": "Blue Area, Islamabad",
        "category": "other",
        "priority": "normal",
        "summary": "Late-night construction noise in residential area",
    },
    {
        "text": "Encroachment by shops on footpath near bus stop, pedestrians forced to walk on road",
        "location": "Saddar Bazaar, Rawalpindi",
        "category": "other",
        "priority": "normal",
        "summary": "Shop encroachment blocking pedestrian footpath",
    },
    {
        "text": "Abandoned car parked on road for 3 months, taking parking space and blocking view",
        "location": "G-11/4, Islamabad",
        "category": "other",
        "priority": "low",
        "summary": "Abandoned vehicle blocking road for months",
    },
]


async def seed() -> None:
    """Insert seed complaints idempotently using deterministic UUIDs."""
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        for item in SEED_DATA:
            # Deterministic UUID from complaint text → idempotent
            seed_id = uuid.uuid5(_NAMESPACE, item["text"])

            await session.execute(
                text(
                    """
                    INSERT INTO complaints (
                        id, complaint_text, location, category, priority,
                        status, ai_summary, triaged_by, triage_latency_ms
                    ) VALUES (
                        :id, :text, :location, CAST(:category AS category_enum),
                        CAST(:priority AS priority_enum), CAST('open' AS status_enum),
                        :summary, 'seed', 0
                    )
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {
                    "id": str(seed_id),
                    "text": item["text"],
                    "location": item["location"],
                    "category": item["category"],
                    "priority": item["priority"],
                    "summary": item["summary"],
                },
            )

        await session.commit()

    await engine.dispose()

    print(f"Seeded {len(SEED_DATA)} complaints (idempotent — duplicates skipped).")


if __name__ == "__main__":
    asyncio.run(seed())
