from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./budget_tracker.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Database Models
class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    amount = Column(Float)
    category = Column(String)
    description = Column(String, nullable=True)
    date = Column(DateTime, default=datetime.utcnow)


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, unique=True, index=True)
    amount = Column(Float)
    month = Column(String)
    year = Column(Integer)


# Create tables
Base.metadata.create_all(bind=engine)


# Pydantic models
class ExpenseCreate(BaseModel):
    title: str
    amount: float
    category: str
    description: Optional[str] = None


class ExpenseResponse(BaseModel):
    id: int
    title: str
    amount: float
    category: str
    description: Optional[str]
    date: datetime

    class Config:
        from_attributes = True


class BudgetCreate(BaseModel):
    category: str
    amount: float
    month: str
    year: int


class BudgetResponse(BaseModel):
    id: int
    category: str
    amount: float
    month: str
    year: int

    class Config:
        from_attributes = True


# FastAPI app
app = FastAPI(title="BudgetTrack API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# API Routes


# Expenses endpoints
@app.post("/api/expenses", response_model=ExpenseResponse)
def create_expense(expense: ExpenseCreate, db: Session = Depends(get_db)):
    db_expense = Expense(**expense.dict())
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense


@app.get("/api/expenses", response_model=List[ExpenseResponse])
def get_expenses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    expenses = db.query(Expense).offset(skip).limit(limit).all()
    return expenses


@app.get("/api/expenses/{expense_id}", response_model=ExpenseResponse)
def get_expense(expense_id: int, db: Session = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@app.put("/api/expenses/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: int, expense: ExpenseCreate, db: Session = Depends(get_db)
):
    db_expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if db_expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")

    for key, value in expense.dict().items():
        setattr(db_expense, key, value)

    db.commit()
    db.refresh(db_expense)
    return db_expense


@app.delete("/api/expenses/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    db_expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if db_expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")

    db.delete(db_expense)
    db.commit()
    return {"message": "Expense deleted successfully"}


# Budget endpoints
@app.post("/api/budgets", response_model=BudgetResponse)
def create_budget(budget: BudgetCreate, db: Session = Depends(get_db)):
    # Check if budget for this category already exists
    existing_budget = (
        db.query(Budget)
        .filter(
            Budget.category == budget.category,
            Budget.month == budget.month,
            Budget.year == budget.year,
        )
        .first()
    )

    if existing_budget:
        # Update existing budget
        existing_budget.amount = budget.amount
        db.commit()
        db.refresh(existing_budget)
        return existing_budget

    db_budget = Budget(**budget.dict())
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    return db_budget


@app.get("/api/budgets", response_model=List[BudgetResponse])
def get_budgets(db: Session = Depends(get_db)):
    budgets = db.query(Budget).all()
    return budgets


# Analytics endpoints
@app.get("/api/analytics/summary")
def get_summary(db: Session = Depends(get_db)):
    total_expenses = db.execute(
        text("SELECT COALESCE(SUM(amount), 0) FROM expenses")
    ).scalar()
    total_budget = db.execute(
        text("SELECT COALESCE(SUM(amount), 0) FROM budgets")
    ).scalar()

    # Category-wise expenses
    category_expenses = db.execute(
        text("""
        SELECT category, SUM(amount) as total 
        FROM expenses 
        GROUP BY category
    """)
    ).fetchall()

    # Recent expenses
    recent_expenses = db.query(Expense).order_by(Expense.date.desc()).limit(5).all()

    return {
        "total_expenses": total_expenses,
        "total_budget": total_budget,
        "remaining_budget": total_budget - total_expenses,
        "category_expenses": [
            {"category": row[0], "amount": row[1]} for row in category_expenses
        ],
        "recent_expenses": recent_expenses,
    }





# Serve index.html at root
@app.get("/")
def read_root():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
