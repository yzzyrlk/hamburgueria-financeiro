"""Modelos SQLAlchemy (espelham sql/schema.sql)."""
from __future__ import annotations
import uuid
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean, Date, DateTime,
    ForeignKey, Enum as SAEnum, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def _uuid():
    return uuid.uuid4()


class Ingredient(Base):
    __tablename__ = "ingredients"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name = Column(Text, nullable=False, unique=True)
    unit = Column(Text, nullable=False)
    unit_cost = Column(Numeric(14, 4), nullable=False, default=0)
    stock_qty = Column(Numeric(14, 4), nullable=False, default=0)
    min_stock_qty = Column(Numeric(14, 4), nullable=False, default=0)
    loss_pct = Column(Numeric(7, 4), nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Product(Base):
    __tablename__ = "products"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    sku = Column(Text, unique=True)
    name = Column(Text, nullable=False)
    category = Column(Text)
    price = Column(Numeric(14, 2), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    recipes = relationship("ProductRecipe", back_populates="product", cascade="all, delete-orphan")


class ProductRecipe(Base):
    __tablename__ = "product_recipes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey("ingredients.id"), nullable=False)
    quantity = Column(Numeric(14, 4), nullable=False)
    product = relationship("Product", back_populates="recipes")
    ingredient = relationship("Ingredient")


class Order(Base):
    __tablename__ = "orders"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    external_id = Column(Text, unique=True)
    channel = Column(SAEnum("balcao", "delivery_proprio", "ifood", "rappi", "99food", "outros",
                            name="order_channel"), nullable=False, default="balcao")
    status = Column(SAEnum("open", "paid", "cancelled", "refunded", name="order_status"),
                    nullable=False, default="open")
    customer_name = Column(Text)
    subtotal = Column(Numeric(14, 2), nullable=False, default=0)
    discount = Column(Numeric(14, 2), nullable=False, default=0)
    delivery_fee = Column(Numeric(14, 2), nullable=False, default=0)
    total = Column(Numeric(14, 2), nullable=False, default=0)
    cmv_total = Column(Numeric(14, 2), nullable=False, default=0)
    notes = Column(Text)
    business_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    quantity = Column(Numeric(14, 4), nullable=False)
    unit_price = Column(Numeric(14, 2), nullable=False)
    unit_cmv = Column(Numeric(14, 2), nullable=False, default=0)
    total_price = Column(Numeric(14, 2), nullable=False)
    total_cmv = Column(Numeric(14, 2), nullable=False, default=0)
    order = relationship("Order", back_populates="items")
    product = relationship("Product")


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    external_id = Column(Text, unique=True)
    method = Column(SAEnum("dinheiro", "pix", "debito", "credito", "vale_refeicao",
                           "marketplace", "outro", name="payment_method"), nullable=False)
    status = Column(SAEnum("pending", "approved", "refused", "refunded", "chargeback",
                           name="transaction_status"), nullable=False, default="pending")
    gross_amount = Column(Numeric(14, 2), nullable=False)
    fees_amount = Column(Numeric(14, 2), nullable=False, default=0)
    net_amount = Column(Numeric(14, 2), nullable=False, default=0)
    installments = Column(Integer, nullable=False, default=1)
    paid_at = Column(DateTime(timezone=True))
    business_date = Column(Date, nullable=False)
    raw_payload = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    order = relationship("Order", back_populates="transactions")
    fees = relationship("TransactionFee", back_populates="transaction", cascade="all, delete-orphan")


class TransactionFee(Base):
    __tablename__ = "transaction_fees"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    fee_type = Column(SAEnum("mdr", "marketplace", "antecipacao", "imposto", "outro", name="fee_type"),
                      nullable=False)
    description = Column(Text)
    rate = Column(Numeric(7, 4))
    amount = Column(Numeric(14, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    transaction = relationship("Transaction", back_populates="fees")


class AccountReceivable(Base):
    __tablename__ = "accounts_receivable"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"))
    description = Column(Text, nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    due_date = Column(Date, nullable=False)
    received_at = Column(DateTime(timezone=True))
    status = Column(SAEnum("pending", "received", "cancelled", name="ar_status"),
                    nullable=False, default="pending")
    bank_account = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AccountPayable(Base):
    __tablename__ = "accounts_payable"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    external_id = Column(Text, unique=True)
    supplier = Column(Text)
    category = Column(Text, nullable=False)
    cost_center = Column(Text)
    description = Column(Text, nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    due_date = Column(Date, nullable=False)
    paid_at = Column(DateTime(timezone=True))
    status = Column(SAEnum("pending", "paid", "cancelled", name="ap_status"),
                    nullable=False, default="pending")
    is_fixed = Column(Boolean, nullable=False, default=False)
    bank_account = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CashFlow(Base):
    __tablename__ = "cash_flow"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    external_id = Column(Text, unique=True)
    direction = Column(SAEnum("in", "out", name="cash_flow_direction"), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(Text)
    bank_account = Column(Text)
    business_date = Column(Date, nullable=False)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now())
    ar_id = Column(UUID(as_uuid=True), ForeignKey("accounts_receivable.id"))
    ap_id = Column(UUID(as_uuid=True), ForeignKey("accounts_payable.id"))
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
