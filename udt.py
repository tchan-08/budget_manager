import sys
import datetime
import random
import math
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QDialog,
    QLineEdit, QFormLayout, QMessageBox, QTextEdit, QInputDialog,
    QComboBox, QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QFileDialog
)
from PyQt5.QtCore import Qt, QDate
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from enum import Enum
import sqlite3 as db

class Transaction_Type(Enum):
    INCOME = "income"
    EXPENSE = "expense"

class Priority_Type(Enum):
    HIGH = 3
    MEDIUM = 2
    LOW = 1

class Chain_Status(Enum):
    OK = 1
    WARNING = -1

class Goal: 

    def __init__(self, goal_id=None, name=None, target=None, deadline=None, progress=0, completed=False, parent_id=None, priority=Priority_Type.LOW): 
        self.goal_id = goal_id 
        if goal_id: 
            self._load_db() 
        else: 
            self.name = name 
            self.target = target 
            self.deadline = deadline 
            self.progress = 0 
            self.completed = completed 
            self.priority = priority 
            self.parent_id = parent_id 

    def _load_db(self): #load data from db if it’s in there, avoid duplication of goals 
        connection = db.connect("database.db") 
        cursor = connection.cursor() 
        query = """SELECT * FROM Goals 
                WHERE id=?;""" 
        cursor.execute(query, (self.goal_id,)) 
        row = cursor.fetchone() 
        connection.close() 
        if row is None: 
            raise ValueError("Goal does not exist") 
        self.goal_id = row[0] 
        self.name = row[1] 
        self.target = row[2] 
        self.deadline = datetime.date.fromisoformat(row[3]) 
        self.progress = row[4] 
        self.completed = bool(row[5]) 
        self.parent_id = row[6] 
        self.priority = Priority_Type[row[7]] 

    def save(self): 
        connection = db.connect("database.db") 
        cursor = connection.cursor() 
        if self.goal_id: #save data to db 
            query = """UPDATE Goals 
                    SET progress = ?, 
                        completed = ?, 
                        priority = ?, 
                        parent_id = ? 
                    WHERE id = ?;""" 
            cursor.execute(query, (self.progress, self.completed, self.priority.name, self.parent_id, self.goal_id)) 
        else: 
            query = """INSERT INTO Goals (name, target, deadline, progress, completed, priority) 
                    VALUES (?, ?, ?, ?, ?, ?);""" 
            cursor.execute(query, (self.name, self.target, self.deadline.isoformat(), self.progress, self.completed, self.priority.name)) 
            self.goal_id = cursor.lastrowid 
        connection.commit() 
        connection.close() 

    def add_contribution(self, amount): 
        try: 
            self.check_valid() #check whether prerequisites complete 
        except Exception as error: 
            return str(error) 
        if self.target - self.progress > amount: 
            self.progress += amount 
        else: 
            self.progress += self.target - self.progress 
        if self.progress == self.target: 
            self.completed = True 
        self.save() 

    def check_valid(self): #recursively check completion of prerequisites 
        if self.parent_id is None: 
            return True 
        parent = Goal(goal_id=self.parent_id) 
        if not(parent.completed): 
            raise Exception(f"{parent.name} prerequisite not completed!") 
        return parent.check_valid() 

    def get_progress(self): 
        return self.progress 

    def days_left(self): 
        today = datetime.date.today() 
        if (self.deadline - today).days < 0: 
            return -1 
        return (self.deadline - today).days 

    def progress_percentage(self): 
        if self.target == 0: 
            return 0 
        return min((self.progress / self.target) * 100, 100) 

    def is_overdue(self): 
        return self.days_left() == -1 and not self.completed #checks whether goal is overdue 

    def mark_completed(self): 
        self.progress = self.target 
        self.completed = True 
        self.save() 

    def get_completed(self): 
        return self.completed 

    def update_priority(self, new_priority): 
        if not isinstance(new_priority, Priority_Type): 
            raise TypeError("Invalid type") 
        self.priority = new_priority 
        self.save() 

    def set_parent(self, parent): 
        if not isinstance(parent, Goal): 
            raise TypeError("Invalid Parent") 
        self.parent_id = parent.goal_id 
        self.save() 

    def get_parent_name(self): #uses goal_id to check whether a parent exists 
        return Goal(goal_id=self.parent_id).name if self.parent_id else None 

    def get_root(self): #recursively checks parents until goal has no parents, root found 
        if self.parent_id is None: 
            return self 
        return Goal(goal_id=self.parent_id).get_root() 

    def chain_cost(self): #recursively sums each cost of a prerequisite chain 
        if self.parent_id is None: 
            return self.target 
        return self.target + Goal(goal_id=self.parent_id).chain_cost()
    
class Recurring_Item():
    def __init__(self, rec_id=None, name=None, rec_type=None, target=None, frequency=None, start_date=None):
        self.rec_id = rec_id
        if rec_id:
            self._load_db()
        else:
            self.name = name
            self.rec_type = rec_type
            self.target = target
            self.frequency = frequency
            self.next_due = start_date
            self.last_processed = None
            self.start_date = start_date

    def _load_db(self):
        connection = db.connect("database.db")
        cursor = connection.cursor()
        query = """SELECT * From Recurring_Items
                WHERE id = ?;"""
        cursor.execute(query, (self.rec_id,))
        row = cursor.fetchone()
        connection.close()
        if row is None:
            return False
        self.rec_id, self.name, self.rec_type, self.target, self.frequency, self.start_date = row[0], row[1], Transaction_Type[row[2]], row[3], row[4], datetime.datetime.strptime(row[5], "%Y-%m-%d").date()
        self.next_due, self.last_processed = self.start_date, None

    def save(self):
        connection = db.connect("database.db")
        cursor = connection.cursor()
        if self.rec_id:
            query = """UPDATE Recurring_Items
                    SET name = ?,
                        type = ?,
                        target = ?,
                        frequency = ?,
                        start_date = ?
                    WHERE id = ?;"""
            cursor.execute(query, (self.name, self.rec_type.name, self.target, self.frequency, self.start_date.isoformat(), self.rec_id))
        else:
            query = """INSERT INTO Recurring_Items (name, type, target, frequency, start_date)
                    VALUES (?, ?, ?, ?, ?);"""
            cursor.execute(query, (self.name, self.rec_type.name, self.target, self.frequency, self.start_date.isoformat()))
            self.rec_id = cursor.lastrowid
        connection.commit()
        connection.close()

    def is_due(self):
        today = datetime.date.today()
        return today >= self.next_due
    
    def apply(self, balance, expenses, incomes):
        if self.rec_type not in (Transaction_Type.INCOME, Transaction_Type.EXPENSE):
            raise TypeError("rec_type must be an income or an expense")
        recurring = Transaction(
            description=self.name,
            transaction_type=self.rec_type,
            amount=self.target,
            date=self.next_due,
            recurring_id=self.rec_id
        )
        recurring.save() #bug fixed, incomes not registering

        if self.rec_type == Transaction_Type.INCOME:
            incomes.append(recurring)
            balance += self.target
        else:
            expenses.append(recurring)
            balance -= self.target

        self.last_processed = self.next_due
        self.next_due = self.next_due + datetime.timedelta(days=self.frequency)
        self.save()
        return balance
    

class Budget_Report:
    def __init__(self, balance=0.0, expenses=None, incomes=None, recurring=None):
        if balance < 0:
            raise ValueError("Invalid balance. Balance cannot be negative.")
        self._balance = balance
        self._expenses = expenses if expenses is not None else []
        self._incomes = incomes if incomes is not None else []
        self._recurring = recurring if recurring is not None else []

    def get_net_balance(self):
        return sum(t.signed_amount() for t in self._expenses + self._incomes)
    
    def get_recent(self, days):
        recent_expenses, recent_incomes = self._expenses[-days:], self._incomes[-days:]
        return recent_expenses, recent_incomes
        
    
    def recent_to_text(self, recent):
        text = ""
        for expense in recent[0]:
            text += f"Expenses: {expense} \n"
        for income in recent[1]:
            text += f"Incomes: {income}"
        return text

    def create_report(self, detail):
        report = ""
        report += f"Net Balance: {self.get_net_balance()} \n {self.recent_to_text(self.get_recent(detail))}"
        return report
    
class Transaction:
    def __init__(self, t_id=None, description=None, transaction_type=None, amount=None, date=None, goal_id=None, recurring_id=None, is_savings=False):
        self.t_id = t_id
        if t_id:
            self._load_db()
        else:
            if description is None or transaction_type is None or amount is None:
                raise ValueError("Transaction data not complete")
            self.description = description.strip()
            if not isinstance(transaction_type, Transaction_Type):
                raise TypeError("Type is not valid")
            self.transaction_type = transaction_type
            self.amount = float(amount)
            self.goal_id = goal_id
            self.recurring_id = recurring_id
            self.is_savings = bool(is_savings)
            if date is None:
                self.date = datetime.date.today()
            elif isinstance(date, datetime.date):
                self.date = date
            else:
                raise TypeError("Type is not valid")

    def _load_db(self):
        connection = db.connect("database.db")
        cursor = connection.cursor()
        query = """SELECT * FROM Transactions
                WHERE id = ?;"""
        cursor.execute(query, (self.t_id,))
        row = cursor.fetchone()
        connection.close()
        if row is None:
            raise ValueError("Transaction does not exist")
        self.t_id = row[0]
        self.description = row[1].strip()
        self.transaction_type = Transaction_Type[row[2]]
        self.amount = row[3]
        self.date = datetime.datetime.strptime(row[4], "%Y-%m-%d").date()
        self.goal_id = row[5]
        self.recurring_id = row[6]
        self.is_savings = bool(row[7])

    def save(self):
        connection = db.connect("database.db")
        cursor = connection.cursor()
        if self.t_id: #if transaction already exists, prevent duplicates
            query = """UPDATE Transactions
                    SET description = ?,
                        type = ?,
                        amount = ?,
                        date = ?,
                        goal_id = ?,
                        recurring_id = ?,
                        is_savings = ?,
                    WHERE id = ?;"""
            cursor.execute(query, (self.description, self.transaction_type.name, self.amount, self.date.isoformat(), self.goal_id, self.recurring_id, int(self.is_savings), self.t_id))
        else:
            query = """INSERT INTO Transactions (description, type, amount, date, goal_id, recurring_id, is_savings)
                    VALUES (?, ?, ?, ?, ?, ?, ?);"""
            cursor.execute(query, (self.description, self.transaction_type.name, self.amount, self.date.isoformat(), self.goal_id, self.recurring_id, int(self.is_savings)))
            self.t_id = cursor.lastrowid
        connection.commit()
        connection.close()

    def signed_amount(self):
        if self.transaction_type == Transaction_Type.EXPENSE: 
            return -self.amount #negative amount if expense, positive if income
        return self.amount

    def to_dict(self):
        return {
            "description": self.description,
            "transaction_type": self.transaction_type.name,
            "amount": self.amount,
            "date": self.date.isoformat()
        }

    def to_csv(self):
        return f"{self.description},{self.amount:.2f},{self.transaction_type.name},{self.date.isoformat()}"

    def __str__(self):
        sign = "+" if self.transaction_type == Transaction_Type.INCOME else "-"
        return f"{self.date} | {self.description} | {sign}£{self.amount:.2f}"
    
    def __float__(self):
        return +float(self.amount) if self.transaction_type == Transaction_Type.INCOME else -float(self.amount)
    
class Stack:
    def __init__(self):
        self.items = []
        self.max_size = 12
        self.pointer = -1
    def is_full(self):
        return self.pointer + 1 == self.max_size
    def is_empty(self):
        return self.pointer + 1 == 0
    def push(self, item):
        if self.is_full():
            raise Exception("Stack is full")
        self.pointer += 1
        self.items.append(item)
    def pop(self):
        if self.is_empty():
            raise Exception("Stack is empty")
        item = self.items.pop()
        self.pointer -= 1
        return item
    def peek(self):
        if self.is_empty():
            raise Exception("Stack is empty")
        return self.items[self.pointer]

class Goal_Node:
    def __init__(self, goal, parent=None):
        if not isinstance(goal, Goal):
            raise TypeError("GoalNode requires a Goal instance")

        self.goal = goal          # reference to the existing Goal
        self.parent = parent      # GoalNode or None
        self.children = []        # list of GoalNode

        if parent:
            parent.add_child(self)

    def add_child(self, child_node):
        if not isinstance(child_node, Goal_Node):
            raise TypeError("Child must be a GoalNode")
        child_node.parent = self
        self.children.append(child_node)

    def remove_child(self, child_node):
        if child_node in self.children:
            child_node.parent = None
            self.children.remove(child_node)

    def check_chain(self):
        if self.parent is None:
            return Chain_Status.OK
        if not self.parent.goal.get_completed():
            return Chain_Status.WARNING
        return self.parent.check_chain()