from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum as SAEnum, func
from sqlalchemy.orm import DeclarativeBase, relationship
import enum

class Base(DeclarativeBase): pass

class InvoiceStatus(str, enum.Enum):
    DRAFT="draft"; SENT="sent"; PAID="paid"; PARTIAL="partial"; CANCELLED="cancelled"

class ProjectStatus(str, enum.Enum):
    ACTIVE="active"; COMPLETED="completed"; PAUSED="paused"; CANCELLED="cancelled"

class PaymentMethod(str, enum.Enum):
    CASH="cash"; CARD="card"; TRANSFER="transfer"; CRYPTO="crypto"; OTHER="other"

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(20))
    company = Column(String(200))
    address = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    projects = relationship("Project", back_populates="client", lazy="selectin")
    invoices = relationship("Invoice", back_populates="client", lazy="selectin")

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="SET NULL"))
    budget = Column(Float, default=0)
    status = Column(SAEnum(ProjectStatus), default=ProjectStatus.ACTIVE)
    created_at = Column(DateTime, default=func.now())
    client = relationship("Client", back_populates="projects")
    invoices = relationship("Invoice", back_populates="project", lazy="selectin")
    expenses = relationship("Expense", back_populates="project", lazy="selectin", cascade="all, delete-orphan")
    work_logs = relationship("WorkLog", back_populates="project", lazy="selectin")

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True)
    invoice_number = Column(String(50), unique=True, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"))
    status = Column(SAEnum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    discount = Column(Float, default=0)
    tax_rate = Column(Float, default=9)
    notes = Column(Text)
    paid_amount = Column(Float, default=0)
    created_at = Column(DateTime, default=func.now())
    client = relationship("Client", back_populates="invoices")
    project = relationship("Project", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", lazy="selectin", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", lazy="selectin", cascade="all, delete-orphan")
    @property
    def subtotal(self): return sum(i.total for i in self.items)
    @property
    def tax_amount(self): return round(self.subtotal * self.tax_rate / 100, 0)
    @property
    def total(self): return self.subtotal + self.tax_amount - (self.discount or 0)
    @property
    def remaining(self): return self.total - (self.paid_amount or 0)

class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    description = Column(String(500), nullable=False)
    quantity = Column(Float, default=1)
    unit = Column(String(50), default="عدد")
    unit_price = Column(Float, nullable=False)
    invoice = relationship("Invoice", back_populates="items")
    @property
    def total(self): return self.quantity * self.unit_price

class Worker(Base):
    __tablename__ = "workers"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(20))
    skill = Column(String(200))
    daily_rate = Column(Float, default=0)
    created_at = Column(DateTime, default=func.now())
    work_logs = relationship("WorkLog", back_populates="worker", lazy="selectin", cascade="all, delete-orphan")
    payments = relationship("WorkerPayment", back_populates="worker", lazy="selectin", cascade="all, delete-orphan")
    @property
    def total_worked(self): return sum(l.total_pay for l in self.work_logs)
    @property
    def total_paid(self): return sum(p.amount for p in self.payments)
    @property
    def balance(self): return self.total_worked - self.total_paid

class WorkLog(Base):
    __tablename__ = "work_logs"
    id = Column(Integer, primary_key=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"))
    date = Column(DateTime, default=func.now())
    hours = Column(Float, default=8)
    description = Column(Text)
    daily_rate = Column(Float, default=0)
    worker = relationship("Worker", back_populates="work_logs")
    project = relationship("Project", back_populates="work_logs")
    @property
    def total_pay(self): return round(self.hours * self.daily_rate / 8, 0) if self.daily_rate else 0

class WorkerPayment(Base):
    __tablename__ = "worker_payments"
    id = Column(Integer, primary_key=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    method = Column(SAEnum(PaymentMethod), default=PaymentMethod.CASH)
    description = Column(Text)
    date = Column(DateTime, default=func.now())
    worker = relationship("Worker", back_populates="payments")

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    amount = Column(Float, nullable=False)
    method = Column(SAEnum(PaymentMethod), default=PaymentMethod.CASH)
    description = Column(Text)
    date = Column(DateTime, default=func.now())
    invoice = relationship("Invoice", back_populates="payments")

class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    category = Column(String(100), nullable=False)
    description = Column(Text)
    amount = Column(Float, nullable=False)
    date = Column(DateTime, default=func.now())
    project = relationship("Project", back_populates="expenses")
