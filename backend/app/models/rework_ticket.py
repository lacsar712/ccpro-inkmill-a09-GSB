from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

REWORK_TICKET_STATUSES = ("open", "rework_done", "closed")


class ReworkTicket(Base):
    __tablename__ = "rework_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("mills.id", ondelete="CASCADE"), nullable=False
    )
    complaint_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    severity_pa_s: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    mill: Mapped["Mill"] = relationship("Mill", back_populates="rework_tickets")
