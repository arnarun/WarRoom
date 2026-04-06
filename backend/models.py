from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, Float, Integer, TIMESTAMP, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import NUMERIC
from database import Base


class Article(Base):
    __tablename__ = "articles"

    id:           Mapped[int]                = mapped_column(Integer, primary_key=True)
    source:       Mapped[str]                = mapped_column(String(100), nullable=False)
    category:     Mapped[Optional[str]]      = mapped_column(String(50))
    region:       Mapped[Optional[str]]      = mapped_column(String(50))
    title:        Mapped[str]                = mapped_column(Text, nullable=False)
    summary:      Mapped[Optional[str]]      = mapped_column(Text)
    url:          Mapped[str]                = mapped_column(Text, unique=True, nullable=False)
    image_url:    Mapped[Optional[str]]      = mapped_column(Text)
    published_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    fetched_at:   Mapped[datetime]           = mapped_column(TIMESTAMP, default=datetime.utcnow)
    tags:         Mapped[Optional[List[str]]]= mapped_column(ARRAY(Text))
    country:      Mapped[Optional[str]]      = mapped_column(String(50))


class MarketPrice(Base):
    __tablename__ = "market_prices"

    symbol:     Mapped[str]            = mapped_column(String(20), primary_key=True)
    type:       Mapped[str]            = mapped_column(String(20), nullable=False)
    name:       Mapped[Optional[str]]  = mapped_column(String(100))
    price:      Mapped[float]          = mapped_column(NUMERIC(20, 8), nullable=False)
    change_1h:  Mapped[Optional[float]]= mapped_column(Float)
    change_24h: Mapped[Optional[float]]= mapped_column(Float)
    change_7d:  Mapped[Optional[float]]= mapped_column(Float)
    volume_24h: Mapped[Optional[float]]= mapped_column(Float)
    market_cap: Mapped[Optional[float]]= mapped_column(Float)
    updated_at: Mapped[datetime]       = mapped_column(TIMESTAMP, default=datetime.utcnow)


class OsintSignal(Base):
    __tablename__ = "osint_signals"

    id:           Mapped[int]                = mapped_column(Integer, primary_key=True)
    source:       Mapped[str]                = mapped_column(String(50), nullable=False)
    type:         Mapped[str]                = mapped_column(String(50), nullable=False)
    severity:     Mapped[Optional[str]]      = mapped_column(String(20))
    title:        Mapped[str]                = mapped_column(Text, nullable=False)
    description:  Mapped[Optional[str]]      = mapped_column(Text)
    url:          Mapped[Optional[str]]      = mapped_column(Text)
    country:      Mapped[Optional[str]]      = mapped_column(String(100))
    published_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    fetched_at:   Mapped[datetime]           = mapped_column(TIMESTAMP, default=datetime.utcnow)


class SocialPost(Base):
    __tablename__ = "social_posts"

    id:           Mapped[int]                = mapped_column(Integer, primary_key=True)
    platform:     Mapped[str]                = mapped_column(String(30), nullable=False)
    community:    Mapped[Optional[str]]      = mapped_column(String(100))
    title:        Mapped[str]                = mapped_column(Text, nullable=False)
    url:          Mapped[Optional[str]]      = mapped_column(Text, unique=True)
    score:        Mapped[Optional[int]]      = mapped_column(Integer)
    num_comments: Mapped[Optional[int]]      = mapped_column(Integer)
    sentiment:    Mapped[Optional[str]]      = mapped_column(String(20))
    published_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    fetched_at:   Mapped[datetime]           = mapped_column(TIMESTAMP, default=datetime.utcnow)
