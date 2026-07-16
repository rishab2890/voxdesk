"""Seed a demo organization with an agent, knowledge doc and a simulated call.

    cd apps/api && python ../../scripts/seed.py

Demo login: demo@voxdesk.app / demo1234!
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Agent, Document, KnowledgeBase, Membership, Organization, Role, User  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services import rag, voice  # noqa: E402

FAQ = b"""VoxDesk Demo Clinic. Hours: Monday to Friday 9am-5pm.
Address: 100 Main Street. Parking is free behind the building.
New patients should arrive 15 minutes early. We accept most insurance plans."""


async def main() -> None:
    async with SessionLocal() as db:
        existing = (await db.execute(select(User).where(User.email == "demo@voxdesk.app"))).scalar_one_or_none()
        if existing:
            print("Seed data already present, nothing to do.")
            return

        user = User(email="demo@voxdesk.app", password_hash=hash_password("demo1234!"), name="Demo Owner")
        org = Organization(name="Demo Clinic", industry="general")
        db.add_all([user, org])
        await db.flush()
        db.add(Membership(user_id=user.id, organization_id=org.id, role=Role.owner))
        kb = KnowledgeBase(organization_id=org.id)
        agent = Agent(organization_id=org.id, name="Front Desk AI", transfer_number="+15551112222",
                      greeting="Thanks for calling Demo Clinic! How can I help?")
        db.add_all([kb, agent])
        await db.flush()

        doc = Document(organization_id=org.id, knowledge_base_id=kb.id, filename="faq.txt")
        db.add(doc)
        await db.flush()
        await rag.ingest_document(db, doc, FAQ)

        await voice.simulate_call(db, agent, "+15550001111", ["What are your opening hours?"])
        await voice.simulate_call(db, agent, "+15550002222", ["I want to book an appointment"])
        await voice.simulate_call(db, agent, "+15550003333", ["Let me talk to a human"])

        await db.commit()
        print("Seeded: demo@voxdesk.app / demo1234! (org: Demo Clinic, 3 sample calls)")


if __name__ == "__main__":
    asyncio.run(main())
