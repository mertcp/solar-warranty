from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    region: Mapped[str] = mapped_column(String(64))
    rated_kwp: Mapped[float] = mapped_column(Float)
    guaranteed_pr: Mapped[float] = mapped_column(Float)
    warranty_start: Mapped[date] = mapped_column(Date)
    inverter_model: Mapped[str] = mapped_column(String(64))
    inverter_serial: Mapped[str] = mapped_column(String(32))
    performance_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    kwh_gap: Mapped[float] = mapped_column(Float, default=0.0)
    thermal_stress: Mapped[float] = mapped_column(Float, default=0.0)
    sla_days_late: Mapped[int] = mapped_column(Integer, default=0)
    state: Mapped[str] = mapped_column(String(32), default="healthy")

    strings: Mapped[list["StringUnit"]] = relationship(back_populates="site")
    readings: Mapped[list["Reading"]] = relationship(back_populates="site")
    milestones: Mapped[list["Milestone"]] = relationship(back_populates="site")
    events: Mapped[list["Event"]] = relationship(back_populates="site")
    claim_drafts: Mapped[list["ClaimDraft"]] = relationship(back_populates="site")


class StringUnit(Base):
    __tablename__ = "strings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"))
    label: Mapped[str] = mapped_column(String(16))
    module_temp_c: Mapped[float] = mapped_column(Float, default=0.0)

    site: Mapped[Site] = relationship(back_populates="strings")
    readings: Mapped[list["Reading"]] = relationship(back_populates="string_unit")


class Reading(Base):
    __tablename__ = "readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"))
    string_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strings.id"), nullable=True)
    recorded_on: Mapped[date] = mapped_column(Date)
    metric: Mapped[str] = mapped_column(String(48))
    value: Mapped[float] = mapped_column(Float)

    site: Mapped[Site] = relationship(back_populates="readings")
    string_unit: Mapped[Optional[StringUnit]] = relationship(back_populates="readings")


class Milestone(Base):
    __tablename__ = "milestones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"))
    kind: Mapped[str] = mapped_column(String(64))
    planned_on: Mapped[date] = mapped_column(Date)
    actual_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    site: Mapped[Site] = relationship(back_populates="milestones")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime)
    summary: Mapped[str] = mapped_column(Text)
    fault_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    site: Mapped[Site] = relationship(back_populates="events")


class ClaimDraft(Base):
    __tablename__ = "claim_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    action: Mapped[str] = mapped_column(Text)
    window: Mapped[str] = mapped_column(String(64))
    kwh_at_risk: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    edited_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    site: Mapped[Site] = relationship(back_populates="claim_drafts")
