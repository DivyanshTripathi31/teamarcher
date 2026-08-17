"""Idempotent initialization for data owned by the existing application."""
from sqlalchemy.orm import Session

from .database import engine
from .models import SiteContent
from .seed import seed


def bootstrap_database() -> None:
    """Seed explicitly enabled accounts and create the one default content row."""
    with Session(engine) as db:
        seed(db)
        if db.get(SiteContent, 1):
            return
        db.add(
            SiteContent(
                id=1,
                project_name="ARCHER",
                tagline="A living record of our software engineering project.",
                description="Archer brings the project’s planning, progress, and presentation history into one clear, permanent public portal.",
                problem="Add the real problem statement for Archer here.",
                objectives="Add the specific, measurable objectives the team agrees on.",
                intended_users="Add the people Archer is being built for.",
                core_features="Add the key capabilities that define Archer.",
                roles_json='{"Divyansh Tripathi":"Role to be assigned","Lavish Gambhir":"Role to be assigned","Mehardeep Singh":"Role to be assigned","Vidit Gupta":"Role to be assigned"}',
            )
        )
        db.commit()
