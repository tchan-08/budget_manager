#IMPORTS

import sys
import datetime
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
import matplotlib.dates as dates
import numpy as np
import sqlite3 as db
from udt import (
    Goal,
    Transaction,
    Recurring_Item,
    Budget_Report,
    Transaction_Type,
    Priority_Type,
    Stack,
)
from algorithms import (
    Goal_Allocator,
    Predictor
)
# pyqt dialog for goal creation
class Goal_Dialog(QDialog):
    def __init__(self, parent=None):
        #inherit methods from QDialog
        super().__init__(parent)
        self.setWindowTitle("Create New Goal")
        self.setModal(True)
        layout = QFormLayout(self)
        #select parameters for the goal
        self.name_edit = QLineEdit()
        self.target_edit = QLineEdit()
        self.days_edit = QLineEdit()
        self.priority_box = QComboBox()
        self.priority_box.addItems(["LOW", "MEDIUM", "HIGH"])

        layout.addRow("Goal Name:", self.name_edit)
        layout.addRow("Target Amount (£):", self.target_edit)
        layout.addRow("Time Limit (days):", self.days_edit)
        layout.addRow("Goal Priority:", self.priority_box)

        btn_ok = QPushButton("Create Goal")
        btn_ok.clicked.connect(self.accept)
        layout.addWidget(btn_ok)

    def get_data(self):
        name = self.name_edit.text().strip()
        try:
            target = float(self.target_edit.text())
            days = int(self.days_edit.text())
        except ValueError:
            target = 0
            days = 0
        deadline = datetime.date.today() + datetime.timedelta(days=days)
        priority = Priority_Type[self.priority_box.currentText()]
        goal = Goal(
            name=name,
            target=target,
            deadline=deadline,
            priority=priority
        )
        return goal


#pyqt5 goal widget
class Goal_Item(QWidget):
    def __init__(self, goal, on_contribute, on_delete, parent=None):
        super().__init__(parent)
        self.goal = goal
        self.main = parent

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        #buttons and information
        info_layout = QHBoxLayout()
        self.label = QLabel(self.format_text())
        info_layout.addWidget(self.label)

        self.add_button = QPushButton("+")
        self.add_button.setFixedWidth(30)
        self.add_button.clicked.connect(lambda: on_contribute(self.goal))
        info_layout.addWidget(self.add_button)

        self.score_goal = QPushButton("?")
        self.score_goal.setFixedWidth(30)
        self.score_goal.clicked.connect(lambda: parent.score_goal(self.goal))
        info_layout.addWidget(self.score_goal)

        self.del_button = QPushButton("X")
        self.del_button.setFixedWidth(30)
        self.del_button.clicked.connect(lambda: on_delete(self.goal))
        info_layout.addWidget(self.del_button)

        self.btn_parent = QPushButton("P")
        self.btn_parent.setFixedWidth(30)
        self.btn_parent.clicked.connect(self.choose_parent)
        info_layout.addWidget(self.btn_parent)

        self.btn_children = QPushButton("C")
        self.btn_children.setFixedWidth(30)
        self.btn_children.clicked.connect(self.show_children)
        info_layout.addWidget(self.btn_children)

        self.btn_chain = QPushButton("*")
        self.btn_chain.setFixedWidth(30)
        self.btn_chain.clicked.connect(self.get_chain_cost)
        info_layout.addWidget(self.btn_chain)

        self.btn_root = QPushButton("R")
        self.btn_root.setFixedWidth(30)
        self.btn_root.clicked.connect(self.get_goal_root)
        info_layout.addWidget(self.btn_root)

        layout.addLayout(info_layout)
        self.progress = QProgressBar()
        self.progress.setValue(self.calc_progress())
        layout.addWidget(self.progress)

    def format_text(self):
        goal = self.goal
        return f"£{goal.get_progress():.2f}/£{goal.target:.2f} – {goal.name} ({goal.days_left()} days left) (Priority: {goal.priority.name})"
    
    def calc_progress(self):
        if self.goal.target <= 0:
            return 0
        return int(self.goal.progress_percentage())

    def update_display(self):
        self.label.setText(self.format_text())
        self.progress.setValue(self.calc_progress())
    
    def show_children(self):
        for goal in self.main.goals:
            print(goal.get_parent_name(), "***")
        children = [goal.name for goal in self.main.goals if goal.parent_id == self.goal.goal_id]
        print(children)
        if not children:
            QMessageBox.information(self, "Children", "This goal has no children.")
            return

        QMessageBox.information(
            self,
            "child goals",
            "Children: " +"\n".join(children)
        )

    def choose_parent(self):
        names = [goal.name for goal in self.main.goals if goal is not self.goal]
        if not names:
            QMessageBox.information(self, "no goal", "No other goals available.")
            return

        name, ok = QInputDialog.getItem(
            self,
            "Choose Parent Goal",
            "Parent:",
            names,
            editable=False
        )

        if ok:
            parent_goal = next(goal for goal in self.main.goals if goal.name == name)
            try:
                if parent_goal.goal_id == self.goal.parent_id: #prevent duplicate parenting
                    raise Exception(f"{parent_goal.name} is already parented to this goal")
                if parent_goal.parent_id and parent_goal.parent_id == self.goal.goal_id: #prevent circular relationship
                    raise Exception("Circular relationship found")
                self.goal.set_parent(parent_goal)
                QMessageBox.information(self, "Prerequisite set", f"{parent_goal.name} is now a prerequisite for {self.goal.name}")
                print(parent_goal.name)
            except TypeError as error:
                QMessageBox.warning(self, "Invalid prerequisite", str(error))
            except Exception as error:
                QMessageBox.warning(self, "Invalid prerequisite", str(error))

        
    def get_chain_cost(self):
        cost = self.goal.chain_cost()
        QMessageBox.information(self, "Chain Cost", f"{self.goal.name} chain cost: {cost}")
    
    def get_goal_root(self):
        root = self.goal.get_root()
        QMessageBox.information(self, f"Root for {self.goal.name}", f"Root: {root.name}")


#pyqt5 recurring creation gui
class Recurring_Dialog(QDialog):
    def __init__(self, recurring_items, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Recurring Payments")
        self.setModal(True)
        self.recurring_items = recurring_items

        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Type", "Name", "Amount (£)", "Frequency", "Next Due"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        self.refresh_table()

        #recurring forms
        form = QFormLayout()
        self.type_box = QComboBox()
        self.type_box.addItems(["Expense", "Income"])
        self.name_edit = QLineEdit()
        self.target_edit = QLineEdit()
        self.freq_box = QComboBox()
        self.freq_box.addItems(["Daily", "Weekly", "Monthly"])
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)

        form.addRow("Type:", self.type_box)
        form.addRow("Name:", self.name_edit)
        form.addRow("Amount (£):", self.target_edit)
        form.addRow("Frequency:", self.freq_box)
        form.addRow("Next Due:", self.date_edit)
        layout.addLayout(form)

        btn_add = QPushButton("Add Recurring Item")
        btn_add.clicked.connect(self.add_recurring)
        layout.addWidget(btn_add)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def refresh_table(self):
        self.table.setRowCount(0)
        for item in self.recurring_items:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(item.rec_type.value.capitalize()))
            self.table.setItem(row, 1, QTableWidgetItem(item.name))
            self.table.setItem(row, 2, QTableWidgetItem(f"{item.target:.2f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{item.frequency} days"))
            self.table.setItem(row, 4, QTableWidgetItem(item.next_due.isoformat()))

    def add_recurring(self):
        try:
            target = float(self.target_edit.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid", "Enter a valid amount.")
            return
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid", "Please enter a name.")
            return
        if self.type_box.currentText() == "Expense":
            rec_type = Transaction_Type.EXPENSE
        else:
            rec_type = Transaction_Type.INCOME

        freq_dict = {
            "Daily": 1,
            "Weekly": 7,
            "Monthly": 30
        }

        frequency = freq_dict[self.freq_box.currentText()]
        start_date = self.date_edit.date().toPyDate()
        item = Recurring_Item(name=name, rec_type=rec_type, target=target, frequency=frequency, start_date=start_date)
        item.save()
        self.recurring_items.append(item)
        self.refresh_table()
        self.name_edit.clear()
        self.target_edit.clear()


class Allocator_Dialog(QDialog):# allocator pyqt5 menu
    def __init__(self, current_balance, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Allocate Budget")
        self.setModal(True)

        layout = QFormLayout(self)

        #choose the algorithm
        self.algorithm_box = QComboBox()
        self.algorithm_box.addItems([
            "Greedy (priority-based)",
            "0/1 Knapsack (optimal)"
        ])

        # choose budget type
        self.budget_mode_box = QComboBox()
        self.budget_mode_box.addItems([
            "Use current balance",
            "Enter custom budget"
        ])

        self.budget_edit = QLineEdit()
        self.budget_edit.setPlaceholderText(f"Current balance: £{current_balance:.2f}")
        self.budget_edit.setEnabled(False)

        self.budget_mode_box.currentIndexChanged.connect(
            lambda i: self.budget_edit.setEnabled(i == 1)
        )

        layout.addRow("Algorithm:", self.algorithm_box)
        layout.addRow("Budget option:", self.budget_mode_box)
        layout.addRow("Available budget (£):", self.budget_edit)

        btn = QPushButton("Allocate")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

    def get_settings(self, current_balance):
        # budget
        if self.budget_mode_box.currentIndex() == 0:
            available = current_balance
        else:
            try:
                available = float(self.budget_edit.text())
            except ValueError:
                available = 0

        # algorithm
        algorithm = (
            "greedy"
            if self.algorithm_box.currentIndex() == 0
            else "knapsack"
        )

        return algorithm, available


#graph windows
class Graph_Dialog(QDialog):
    def __init__(self, goals, transactions, balance, predictive_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Graphs & Statistics")
        self.resize(900, 600)

        self.predictive_data = predictive_data
        self.predictive_income = self.predictive_data.get("income")

        layout = QVBoxLayout(self)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        print(f"predictive income: {self.predictive_income}")
        self.plot_graphs(goals, transactions, balance)

    def get_date(self, transaction):
        return transaction.date


    def plot_graphs(self, goals, transactions, balance):
        self.figure.clear()

        ax1 = self.figure.add_subplot(131)
        ax2 = self.figure.add_subplot(132)
        ax3 = self.figure.add_subplot(133)

        expenses = [transaction for transaction in transactions if transaction.transaction_type == Transaction_Type.EXPENSE and not transaction.is_savings]
        if expenses:
            expense_dict = {}
            for expense in expenses:
                print(expense, "AAAAAAA")
                expense_dict[expense.description] = expense_dict.get(expense.description, 0) + expense.amount
            labels = list(expense_dict.keys())
            amounts = list(expense_dict.values())
            ax1.pie(amounts, labels=labels, autopct='%1.1f%%', startangle=90)
        ax1.set_title("Expense Distribution")

        incomes = [transaction for transaction in transactions if transaction.transaction_type == Transaction_Type.INCOME]
        if incomes:
            incomes.sort(key=lambda transaction: transaction.date)
            income_dates = [transaction.date for transaction in incomes] 
            amounts = [transaction.amount for transaction in incomes]

            # plot actual income
            ax2.plot(income_dates, amounts, marker='o', linestyle='-', color='blue', label="Actual Income")

            # extrapolate using linear function
            if len(income_dates) > 1:
                #fit with y = mx + c
                x = np.array([dates.date2num(date) for date in income_dates])#dates on x
                y = np.array(amounts)#incomes on y
                best_fit = np.polyfit(x, y, 1)#get gradient and y intercept for a linear function i.e. polynomial degree of one
                trend_func = np.poly1d(best_fit)

                #3 months future data
                future_dates = [income_dates[-1] + datetime.timedelta(days=30*i) for i in range(1, 4)]
                future_x = np.array([dates.date2num(date) for date in future_dates])
                future_y = trend_func(future_x)
                ax2.plot(future_dates, future_y, linestyle='--', marker='o', color='orange', label="Predicted Income")

            ax2.xaxis.set_major_formatter(dates.DateFormatter('%Y-%m-%d'))
            self.figure.autofmt_xdate(rotation=30)
            ax2.set_xlabel("Date")
            ax2.set_ylabel("Income (£)")
            ax2.set_title("Income Trend & Prediction")
            ax2.legend()

        #plot goals
        if goals:
            goal_names = [goal.name for goal in goals]
            progress = [goal.progress_percentage() for goal in goals]
            predicted = []

            for goal in goals:
                #check if goal has monte carlo attribute
                if hasattr(self, "monte_carlo"):
                    income_amounts = [transaction.amount for transaction in transactions if transaction.transaction_type == Transaction_Type.INCOME]
                    mc_prediction = self.monte_carlo(income_amounts, goal, 1000)
                    predicted_progress = min(progress[goal_names.index(goal.name)] + mc_prediction * 100, 100)
                    predicted.append(predicted_progress)
                else:
                    predicted.append(progress[goal_names.index(goal.name)])

            ax3.bar(goal_names, progress, color='skyblue', label="Current")
            ax3.bar(goal_names, predicted, color='orange', alpha=0.5, label="Predicted")
            ax3.set_ylim(0, 100)
            ax3.set_xticklabels(goal_names, rotation=30, ha='right')
            ax3.set_title("Goal Progress (%)")
            ax3.legend()

        self.figure.tight_layout()
        self.canvas.draw()


#main
class Main_Window(QMainWindow):
    def __init__(self):
        super().__init__()

        self.goals = []
        self.balance = 0.0
        self.savings_balance = 0.0
        self.savings_history = []
        self.recurring_items = []
        self.incomes = []
        self.expenses = []

        self.setWindowTitle("nea")
        self.resize(950, 550)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        left_layout = QVBoxLayout()
        notif_label = QLabel("Notification / Goals Bar")
        notif_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(notif_label)

        self.goal_list = QListWidget()
        left_layout.addWidget(self.goal_list)

        add_goal_btn = QPushButton("Add New Goal")
        add_goal_btn.clicked.connect(self.add_goal)
        left_layout.addWidget(add_goal_btn)

        recurring_btn = QPushButton("Manage Recurring Payments")
        recurring_btn.clicked.connect(self.manage_recurring)
        left_layout.addWidget(recurring_btn)

        apply_btn = QPushButton("Update")
        apply_btn.clicked.connect(self.apply_recurring)
        left_layout.addWidget(apply_btn)

        smart_allocate_btn = QPushButton("Allocate budget automatically")
        smart_allocate_btn.clicked.connect(self.open_allocator)
        left_layout.addWidget(smart_allocate_btn)

        right_layout = QVBoxLayout()
        status_label = QLabel("Status Menu")
        status_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(status_label)

        self.status_box = QTextEdit()
        self.status_box.setReadOnly(True)
        right_layout.addWidget(self.status_box)

        predictive_label = QLabel("Predictive Analytics")
        predictive_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(predictive_label)
        self.predictive_box = QTextEdit()
        self.predictive_box.setReadOnly(True)
        right_layout.addWidget(self.predictive_box)

        graph_btn = QPushButton("View Graphs/Stats")
        graph_btn.clicked.connect(self.open_graphs)
        right_layout.addWidget(graph_btn)

        set_balance_btn = QPushButton("Set/Update Current Balance")
        set_balance_btn.clicked.connect(self.set_balance)
        right_layout.addWidget(set_balance_btn)

        deposit_btn = QPushButton("Deposit into Savings Balance")
        deposit_btn.clicked.connect(self.deposit)
        right_layout.addWidget(deposit_btn)

        withdraw_btn = QPushButton("Withdraw from Savings Balance")
        withdraw_btn.clicked.connect(self.withdraw)
        right_layout.addWidget(withdraw_btn)

        download_status_btn = QPushButton("Download Status")
        download_status_btn.clicked.connect(self.download_status)
        right_layout.addWidget(download_status_btn)

        reset_btn = QPushButton("Reset all")
        reset_btn.clicked.connect(self.reset_all)
        right_layout.addWidget(reset_btn)

        main_layout.addLayout(left_layout, 3)
        main_layout.addLayout(right_layout, 2)
        self.load_data()
        self.update_status()
        self.update_predictive()
        print(self.balance)

    def load_data(self):
        connection = db.connect("database.db")
        cursor = connection.cursor()
        cursor.execute("""SELECT value FROM Info
                WHERE key = 'balance';""")
        row = cursor.fetchone()
        if row is None:
            self.balance = 0.0
        else:
            self.balance = float(row[0])

        #load goals
        cursor.execute("""SELECT id 
                        FROM Goals;""")
        for (goal_id, ) in cursor.fetchall():
            goal = Goal(goal_id=goal_id)
            self.goals.append(goal)
            self._add_goal_widget(goal)

        #load recurring items
        cursor.execute("""SELECT id
                        FROM Recurring_Items;""")
        for (rec_id, ) in cursor.fetchall():
            recurring_item = Recurring_Item(rec_id=rec_id)
            self.recurring_items.append(recurring_item)

        #load transactions
        cursor.execute("""SELECT id
                       FROM Transactions;""")
        for (t_id, ) in cursor.fetchall():
            t = Transaction(t_id=t_id)
            print(t.transaction_type.name)
            self.expenses.append(t) if t.transaction_type == Transaction_Type.EXPENSE else self.incomes.append(t)
        print(f"Incomes loaded: {len(self.incomes)}, Expenses loaded: {len(self.expenses)}")

        #load savings
        cursor.execute("""SELECT id
                       FROM Transactions
                       WHERE is_savings = 1""")
        for (s_id, ) in cursor.fetchall():
            s = Transaction(t_id=s_id)
            self.savings_history.append(s)
        cursor.close()

        self.savings_balance = sum(transaction.amount if transaction.transaction_type == Transaction_Type.INCOME else -transaction.amount for transaction in self.savings_history)
        connection.close()


    # status
    def update_status(self):
        total_expenses = sum(transaction.signed_amount() for transaction in self.expenses if transaction.transaction_type == Transaction_Type.EXPENSE)
        self.status_box.clear()
        
        self.status_box.append(f"Current Balance: £{self.calculate_balance():.2f}")
        self.status_box.append(f"Current Savings Balance: £{self.savings_balance:.2f}")
        self.status_box.append(f"Total Expenses: £{total_expenses:.2f}")
        
        # recent expenses
        self.status_box.append("\nRecent Expenses:")
        if self.expenses:
            for expense in self.expenses[-5:]:
                self.status_box.append(f" - £{expense.amount:.2f} to '{expense.description}' ({expense.date})")
        else:
            self.status_box.append(" None yet.")
        
        # recurring items
        self.status_box.append("\nActive Subscriptions / Recurring Items:")
        if self.recurring_items:
            for recurring_item in self.recurring_items:
                next_due_str = recurring_item.next_due.isoformat() if isinstance(recurring_item.next_due, datetime.date) else str(recurring_item.next_due)
                self.status_box.append(
                    f" - {recurring_item.rec_type.value.capitalize()}: '{recurring_item.name}' £{recurring_item.target:.2f} ({recurring_item.frequency} days), next due: {next_due_str}"
                )
        else:
            self.status_box.append(" None yet.")
        
        # net balance
        self.status_box.append(f"\nNet Balance: £{self.calculate_balance():.2f}")

    # predictive analytics
    def update_predictive(self):
        self.predictive_box.clear()
        if len(self.incomes) < 3 or len(self.expenses) < 3:
            self.predictive_box.append(f"Not enough data for predictions!")
        else:
            w_savings, w_incomes, w_expenses = self.weighted_savings(), self.weighted_incomes(), self.weighted_expenses()
            
            self.predictive_box.append(f"Predicted savings: {w_savings:.2f}")
            self.predictive_box.append(f"Predicted income: {w_incomes:.2f}")
            self.predictive_box.append(f"Predicted expenses: {w_expenses:.2f}")
    
    def weighted_savings(self):
        p = Predictor(self.incomes, self.expenses, self.savings_history)
        weights = [0.4, 0.25, 0.15, 0.12, 0.08]
        savings_stack = Stack()
        for transaction in self.savings_history[-5:]:
            print(transaction.transaction_type, "type")
            if transaction.transaction_type == Transaction_Type.INCOME:
                savings_stack.push(transaction.amount)
                print(savings_stack.items)
            else:
                savings_stack.push(-transaction.amount)
        predicted = p.weighted_predictions(savings_stack, weights)
        return predicted
    
    def weighted_incomes(self):
        p = Predictor(self.incomes, self.expenses, self.savings_history)
        weights = [0.4, 0.25, 0.15, 0.12, 0.08]
        incomes_stack = Stack()
        for transaction in self.incomes[-5:]:
            incomes_stack.push(transaction.amount)
        predicted = p.weighted_predictions(incomes_stack, weights)
        return predicted
    
    def weighted_expenses(self):
        p = Predictor(self.incomes, self.expenses, self.savings_history)
        weights = [0.4, 0.25, 0.15, 0.12, 0.08]
        expenses_stack = Stack()
        for transaction in self.expenses[-5:]:
            expenses_stack.push(transaction.amount)
        predicted = p.weighted_predictions(expenses_stack, weights)
        return predicted
    
    def score_goal(self, goal):
        if not isinstance(goal, Goal):
            QMessageBox.warning("Goal not valid")
            return
        p = Predictor(self.incomes, self.expenses, self.savings_history)
        history = self.monthly_savings()
        if not history:
            QMessageBox.warning(self, "Error", "Insufficient transaction history")
        passes = 1000
        probability = p.monte_carlo(history, goal, passes)
        print(self.calculate_balance())
        score = p.goal_classify(goal, probability, self.calculate_balance())
        print(score)
        rating = ""
        if score == 1:
            rating += "Good!"
        elif score == 0:
            rating += "Okay."
        elif score == -1:
            rating += "Bad."
        QMessageBox.information(self, "Goal Completion Probabilityy", f"Success rate after {passes} trials: {(probability * 100):.2f}%. Overall rating: {rating}")
        self.predictive_box.append(f"\"{goal.name}\" completion probability: {probability * 100:.2f}%. Rating: {rating}")

    # balance and savings

    def save_balance(self):
        connection = db.connect("database.db")
        cursor = connection.cursor()
        query = """INSERT INTO Info (key, value)
                VALUES ('balance', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value;""" #prevent key conflicts, instead, update the row
        cursor.execute(query, (self.calculate_balance(), ))
        connection.commit()
        connection.close()

    def calculate_balance(self):
        total = sum(transaction.signed_amount() for transaction in self.incomes + self.expenses)
        return self.balance + total
    
    def monthly_savings(self):
        monthly = {}  #dictionary, where key is tuple of (year, month), value is withdrawals from savings
        for transaction in self.incomes + self.expenses:
            year_month = (transaction.date.year, transaction.date.month)
            if year_month not in monthly:
                monthly[year_month] = 0
            monthly[year_month] += transaction.signed_amount()
        return list(monthly.values())
    
    #def set_balance(self):
    #    text, ok = QInputDialog.getText(self, "Set Balance", "Enter your current balance (£):")
    #    if ok:
    #        try:
    #            self.balance = float(text)
    #            if self.balance < 0:
    #                raise ValueError
    #        except ValueError:
    #            QMessageBox.warning(self, "Error", "Please enter a valid number.")
    #            return
    #        self.save_balance()
    #    self.update_status()

    def set_balance(self):
        text, ok = QInputDialog.getText(
            self,
            "Set Balance",
            "Enter your current balance (£):"
        )
        if ok:
            try:
                new_display_balance = float(text) #edit GUI
                if float(text) < 0:
                    raise ValueError
            except ValueError:
                QMessageBox.warning(self, "Error", "Please enter a valid number.") #prevent negative balances + erroneous inputs
                return

            transactions_total = sum(
                transaction.signed_amount() for transaction in self.incomes + self.expenses #sum all transactions
            )

            self.balance = new_display_balance - transactions_total
            self.save_balance()

        self.update_status()

    def deposit(self):
        if self.calculate_balance() <= 0:
            QMessageBox.warning(self, "Error", "No money to deposit!")
            return
        amount_text, ok = QInputDialog.getText(
            self, "Deposit to savings", f"Enter amount to deposit. Current savings: £{self.savings_balance:.2f}"
        )
        if ok:
            try:
                amount = float(amount_text)
            except ValueError:
                QMessageBox.warning(self, "Error", "Enter a valid number")
                return
            if amount <= 0:
                QMessageBox.warning(self, "Error", "Amount must be positive")
                return
            if amount > self.calculate_balance():
                QMessageBox.warning(self, "Error", "Insufficient funds")
                return

            #update savings 
            self.savings_balance += amount
            self.balance -= amount

            transaction = Transaction(
                description="Deposit to savings",
                transaction_type=Transaction_Type.EXPENSE,
                amount=amount,
                date=datetime.date.today(),
                is_savings=True
            )
            self.savings_history.append(transaction)
            self.expenses.append(transaction)

            # save to db
            connection = db.connect("database.db")
            cursor = connection.cursor()
            cursor.execute(
                """INSERT INTO Transactions (description, type, amount, date, is_savings)
                VALUES (?, ?, ?, ?, ?);""",
                ("Deposit to savings", Transaction_Type.EXPENSE.name, amount, datetime.date.today(), 1)
            )
            connection.commit()
            connection.close()

            self.update_status()
            self.update_predictive()
            QMessageBox.information(
                self, "Successful",
                f"£{amount:.2f} deposited into savings! Current savings: £{self.savings_balance:.2f}, balance: £{self.calculate_balance():.2f}"
            )
            self.save_balance()


    def withdraw(self):
        if self.savings_balance <= 0:
            QMessageBox.warning(self, "Error", "No money to withdraw!")
            return
        amount_text, ok = QInputDialog.getText(
            self, "Withdraw from savings", f"Enter amount to withdraw. Current savings: £{self.savings_balance:.2f}"
        )
        if ok:
            try:
                amount = float(amount_text)
            except ValueError:
                QMessageBox.warning(self, "Error", "Enter a valid number")
                return
            if amount <= 0:
                QMessageBox.warning(self, "Error", "Amount must be positive")
                return
            if amount > self.savings_balance:
                QMessageBox.warning(self, "Error", "Insufficient savings")
                return

            #update savings
            self.savings_balance -= amount
            self.balance += amount

            transaction = Transaction(
                description="Withdraw from savings",
                transaction_type=Transaction_Type.INCOME,
                amount=amount,
                date=datetime.date.today(),
                is_savings=True
            )
            self.savings_history.append(transaction)
            self.incomes.append(transaction)

            # save to db
            connection = db.connect("database.db")
            cursor = connection.cursor()
            cursor.execute(
                """INSERT INTO Transactions (description, type, amount, date, is_savings)
                VALUES (?, ?, ?, ?, ?);""",
                ("Withdrawal from savings", Transaction_Type.INCOME.name, amount, datetime.date.today(), 1)
            )
            connection.commit()
            connection.close()

            self.update_status()
            self.update_predictive()
            QMessageBox.information(
                self, "Successful",
                f"£{amount:.2f} withdrawn from savings! Current savings: £{self.savings_balance:.2f}, balance: £{self.calculate_balance():.2f}"
            )
            self.save_balance()

    # download
    def download_status(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Status", "", "CSV Files (*.csv);;Text Files (*.txt)")
        if not file_path:
            return

        lines = []
        lines.append(f"Current Balance,£{self.balance:.2f}")
        total_expenses = sum(transaction.amount for transaction in self.expenses)
        lines.append(f"Total Expenses,£{total_expenses:.2f}")
        lines.append("\nRecent Expenses")
        lines.append("Goal,Amount (£),Date")
        for expense in self.expenses[-5:]:
            lines.append(f"{expense.description},{expense.amount:.2f},{expense.date}")
        
        lines.append("\nRecurring Items")
        lines.append("Type,Name,Amount (£),Frequency,Next Due")
        frequencies = {1: "day",
                       7: "week",
                       30: "month"}
        for recurring in self.recurring_items:
            next_due_str = recurring.next_due.isoformat() if isinstance(recurring.next_due, datetime.date) else str(recurring.next_due)
            lines.append(f"{recurring.rec_type.value.capitalize()},{recurring.name},{recurring.target:.2f},{frequencies[recurring.frequency].capitalize()},{next_due_str}")
        
        lines.append(f"\nNet Balance,£{self.balance - total_expenses:.2f}")

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            QMessageBox.information(self, "Saved", f"Status saved to {file_path}")
        except Exception as error:
            QMessageBox.warning(self, "Error", f"Failed to save file:\n{error}")

    # goals
    def add_goal(self):
        dialog = Goal_Dialog(self)
        if dialog.exec_() == QDialog.Accepted:
            goal = dialog.get_data()
            if not goal.name or goal.target <= 0 or goal.days_left() <= 0:
                QMessageBox.warning(self, "Invalid", "Please enter a valid goal.")
                return
            goal.save()
            self.goals.append(goal)
            self._add_goal_widget(goal)

    def _add_goal_widget(self, goal):
        item = QListWidgetItem(self.goal_list)
        widget = Goal_Item(goal, self.contribute_to_goal, self.delete_goal, parent=self)
        item.setSizeHint(widget.sizeHint())
        self.goal_list.addItem(item)
        self.goal_list.setItemWidget(item, widget)

    def contribute_to_goal(self, goal):
        amount_text, ok = QInputDialog.getText(self, "Contribute", f"How much to add towards '{goal.name}'?")
        if ok:
            try:
                amount = float(amount_text)
            except ValueError:
                QMessageBox.warning(self, "Error", "Invalid amount.")
                return
            if amount <= 0:
                QMessageBox.warning(self, "Error", "Amount must be > 0.")
                return
            if amount > self.calculate_balance():
                print(self.balance)
                QMessageBox.warning(self, "Error", "Insufficient funds.")
                return
            if amount > goal.target:
                QMessageBox.warning(self, "Error", "Overspending!")
                return
            
            if goal.completed:
                QMessageBox.warning(self, "Error", "Goal already completed.")
            try:
                goal.check_valid()
                goal.add_contribution(amount)
                transaction = Transaction(description=goal.name,transaction_type=Transaction_Type.EXPENSE,amount=amount, goal_id=goal.goal_id)
                transaction.save()
                self.expenses.append(transaction)
                
                self.update_status()
                self.update_predictive()
                self._refresh_goal_widget(goal)
            except Exception as error:
                QMessageBox.warning(self, "Warning", str(error))

    def _refresh_goal_widget(self, goal):
        for i in range(self.goal_list.count()):
            item = self.goal_list.item(i)
            widget = self.goal_list.itemWidget(item)
            if widget.goal is goal:
                widget.update_display()
                break

    def delete_goal(self, goal):
        confirm = QMessageBox.question(self, "Delete Goal", f"Delete goal '{goal.name}'?")
        if confirm == QMessageBox.Yes:
            self.goals.remove(goal)
            for i in range(self.goal_list.count()):
                item = self.goal_list.item(i)
                widget = self.goal_list.itemWidget(item)
                if widget.goal is goal:
                    self.goal_list.takeItem(i)
                    break
            connection = db.connect("database.db")
            cursor = connection.cursor()
            query = """DELETE FROM Goals
                    WHERE id = ?;"""
            cursor.execute(query, (goal.goal_id, ))
            self.update_status()
            connection.commit()
            connection.close()

    #recurring
    def manage_recurring(self):
        dialog = Recurring_Dialog(self.recurring_items, self)
        dialog.exec_()
        self.update_status()
        self.update_predictive()

    def apply_recurring(self):
        changes = 0

        for item in self.recurring_items:
            if item.is_due():
                item.apply(self.balance, self.expenses, self.incomes)
                changes += 1
        self.save_balance()
        QMessageBox.information(
            self,
            "Recurring applied",
            f"{changes} transactions processed"
        )

        self.update_status()
        self.update_predictive()

    # graphh
    def open_graphs(self):
        if len(self.incomes) >= 3 and len(self.expenses) >= 3:
            p = Predictor(self.incomes, self.expenses, self.savings_history)
            predicted_data = {
                "savings": self.weighted_savings(),
                "income": self.weighted_incomes(),
                "expenses": self.weighted_expenses()
            }
            print(predicted_data)
        else:
            predicted_data = {}
        dialog = Graph_Dialog(self.goals, self.expenses + self.incomes, self.balance, predicted_data, self)
        dialog.exec_()
    

    # algorithms
    def open_allocator(self):
        dialog = Allocator_Dialog(self.calculate_balance(), self)
        if dialog.exec_() == QDialog.Accepted:
            algorithm, available = dialog.get_settings(self.calculate_balance())

            if available <= 0:
                QMessageBox.warning(self, "Invalid", "Budget must be greater than 0.")
                return

            self.budget_allocate(algorithm, available)

    def budget_allocate(self, algorithm, available):
        allocator = Goal_Allocator(self.goals, available)
        if algorithm == "knapsack":
            remaining = allocator.allocate_budget()
        else:
            remaining = allocator.greedy()
        
        self.balance = remaining
        self.save_balance()
        
        for goal in self.goals:
            goal.save()
        
        self.goal_list.clear()
        for goal in self.goals:
            self._add_goal_widget(goal)
        
        self.update_status()
        self.update_predictive()

    # miscellaneous

    def reset_all(self):
        confirm = QMessageBox.question(self, "Reset data", "Reset all data?")
        if confirm == QMessageBox.Yes:
            self.balance = 0
            self.incomes.clear()
            self.expenses.clear()
            self.recurring_items.clear()
            self.goals.clear()
            connection = db.connect("database.db")
            cursor = connection.cursor()
            query_1 = """DELETE FROM Goals;"""
            cursor.execute(query_1)
            query_2 = """DELETE FROM Recurring_Items;"""
            cursor.execute(query_2)
            query_3 = """DELETE FROM Transactions;"""
            cursor.execute(query_3)
            query_4 = """DELETE FROM Info;"""
            cursor.execute(query_4)
            connection.commit()
            connection.close()
            self.update_status()
            self.update_predictive()
            self.goal_list.clear()
            self.status_box.clear()
            self.predictive_box.clear()
    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Main_Window()
    win.show()
    sys.exit(app.exec_())