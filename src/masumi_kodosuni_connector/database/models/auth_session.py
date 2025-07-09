"""Database model for storing Kodosumi authentication sessions."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from masumi_kodosuni_connector.database.connection import Base


class AuthSession(Base):
    """Store Kodosumi authentication session data to avoid frequent re-authentication."""
    __tablename__ = "auth_sessions"
    
    service_name = Column(String(50), primary_key=True, default="kodosumi")
    cookie_data = Column(Text, nullable=False)  # JSON serialized cookies
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)