"""Database model for storing Kodosumi authentication sessions."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from masumi_kodosuni_connector.database.connection import Base


class AuthSession(Base):
    """Store Kodosumi authentication session data to avoid frequent re-authentication."""
    __tablename__ = "auth_sessions"
    
    service_name = Column(String(50), primary_key=True, default="kodosumi")
    api_key = Column(Text, nullable=True)  # API key for authentication
    cookie_data = Column(Text, nullable=True)  # JSON serialized cookies (legacy)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)