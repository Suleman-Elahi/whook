from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class Webhook(Base):
    __tablename__ = "webhook"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(200), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    status = Column(Boolean, default=True, nullable=False, index=True)
    transformation_script = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    user = relationship("User", back_populates="webhooks")
    requests = relationship("WebhookRequest", cascade="all, delete-orphan", back_populates="webhook")
    destinations = relationship("Destination", cascade="all, delete-orphan", back_populates="webhook")
    
    __table_args__ = (
        Index('idx_user_webhook', 'user_id', 'id'),
    )


class Destination(Base):
    __tablename__ = "destination"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), nullable=False)
    webhook_id = Column(Integer, ForeignKey("webhook.id", ondelete="CASCADE"), nullable=False, index=True)
    webhook = relationship("Webhook", back_populates="destinations")


class WebhookRequest(Base):
    __tablename__ = "webhook_request"
    
    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey("webhook.id", ondelete="CASCADE"), nullable=False, index=True)
    headers = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    query_params = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    webhook = relationship("Webhook", back_populates="requests")
    
    __table_args__ = (
        Index('idx_webhook_timestamp', 'webhook_id', 'timestamp'),
    )
