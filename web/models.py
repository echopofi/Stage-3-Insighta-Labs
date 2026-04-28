import os
import datetime
import uuid
import hashlib
import secrets
from uuid6 import uuid7
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or "sqlite:///./profiles.db"

if DATABASE_URL.startswith("postgres"):
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5)
else:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

COUNTRY_MAP = {
    "NG": "Nigeria", "US": "United States", "GB": "United Kingdom", "CA": "Canada",
    "KE": "Kenya", "GH": "Ghana", "ZA": "South Africa", "EG": "Egypt",
    "IN": "India", "CN": "China", "JP": "Japan", "BR": "Brazil",
    "MX": "Mexico", "DE": "Germany", "FR": "France", "IT": "Italy",
    "ES": "Spain", "NL": "Netherlands", "BE": "Belgium", "SE": "Sweden",
    "NO": "Norway", "DK": "Denmark", "FI": "Finland", "PL": "Poland",
    "RU": "Russia", "UA": "Ukraine", "TR": "Turkey", "SA": "Saudi Arabia",
    "AE": "United Arab Emirates", "SG": "Singapore", "MY": "Malaysia", "ID": "Indonesia",
    "TH": "Thailand", "VN": "Vietnam", "PH": "Philippines", "KR": "South Korea",
    "AU": "Australia", "NZ": "New Zealand", "AR": "Argentina", "CL": "Chile",
    "CO": "Colombia", "PE": "Peru", "VE": "Venezuela", "BJ": "Benin",
    "TZ": "Tanzania", "UG": "Uganda", "ET": "Ethiopia", "CM": "Cameroon",
    "SN": "Senegal", "CI": "Ivory Coast", "MG": "Madagascar", "MA": "Morocco",
    "DZ": "Algeria", "TN": "Tunisia", "SD": "Sudan", "ZW": "Zimbabwe",
    "ZM": "Zambia", "MW": "Malawi", "MZ": "Mozambique", "BW": "Botswana",
    "NA": "Namibia", "AO": "Angola", "CD": "Democratic Republic of Congo",
    "RW": "Rwanda", "PT": "Portugal", "CH": "Switzerland", "AT": "Austria",
    "IE": "Ireland", "GR": "Greece", "HU": "Hungary", "CZ": "Czech Republic",
    "RO": "Romania", "BG": "Bulgaria", "HR": "Croatia", "RS": "Serbia",
    "SK": "Slovakia", "SI": "Slovenia", "LT": "Lithuania", "LV": "Latvia",
    "EE": "Estonia", "IS": "Iceland", "LU": "Luxembourg", "MT": "Malta",
    "CY": "Cyprus", "PA": "Panama", "CR": "Costa Rica", "GT": "Guatemala",
    "HN": "Honduras", "SV": "El Salvador", "NI": "Nicaragua", "DO": "Dominican Republic",
    "CU": "Cuba", "JM": "Jamaica", "TT": "Trinidad and Tobago", "BB": "Barbados",
    "BS": "Bahamas", "BZ": "Belize", "GY": "Guyana", "SR": "Suriname",
    "BO": "Bolivia", "PY": "Paraguay", "UY": "Uruguay", "EC": "Ecuador"
}


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid7()))
    github_id = Column(String, unique=True, index=True, nullable=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    role = Column(String, default="analyst")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc),
                        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True, default=lambda: str(uuid7()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    code_verifier = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    revoked = Column(Boolean, default=False)


class OAuthState(Base):
    __tablename__ = "oauth_states"

    id = Column(String, primary_key=True, default=lambda: str(uuid7()))
    state = Column(String, unique=True, index=True, nullable=False)
    code_verifier = Column(String, nullable=False)
    redirect_uri = Column(String, nullable=False)
    client_type = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid7()))
    name = Column(String, unique=True, index=True, nullable=False)
    gender = Column(String)
    gender_probability = Column(Float)
    sample_size = Column(Integer)
    age = Column(Integer)
    age_group = Column(String)
    country_id = Column(String)
    country_name = Column(String)
    country_probability = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))


class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid7()))
    user_id = Column(String, nullable=True)
    method = Column(String, nullable=False)
    path = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))


def init_db():
    Base.metadata.create_all(bind=engine)