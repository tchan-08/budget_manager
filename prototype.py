from datetime import datetime, timedelta
class Goal:
    def __init__(self, name, amount, due_date):
        self.name = name
        self.amount = amount
        self.due_date = due_date
        self.progress = 0
        self.completed = False
    def get_info(self):
        return {
            "name": self.name,
            "amount": self.amount,
            "date": self.due_date,
            "progress": self.progress,
            "completed": self.completed
        }
    def contribute(self, amount):
        if self.progress + amount <= self.amount:
            self.progress += amount
        else:
            self.progress = self.amount
        if self.progress == self.amount:
            self.completed = True

class Recurring_Item:
    def __init__(self, name, amount, frequency, transaction_type, initial_date):
        self.name = name
        self.amount = amount
        self.frequency = frequency
        self.transaction_type = transaction_type
        self.completed = False
        self.initial_date = initial_date
    def get_info(self):
        return {
            "name": self.name,
            "amount": self.amount,
            "frequency": self.frequency,
            "initial": self.initial_date,
            "type": self.transaction_type
        }

class Main:
    def __init__(self):
        self.balance = 0
        self.incomes = []
        self.expenses = []
        self.recurring = []
        self.goals = []
        self.today = datetime.now()
    def Main(self):
        while True:
            print("""
BUDGET MANAGER PROTOTYPE
              1. SEE GOALS
              2. SEE RECURRING ITEMS
              3. SEE STATUS
              4. CONTRIBUTE TO GOAL
              5. APPLY RECURRING
              6. ADD GOAL
              7. ADD RECURRING
              8. ADD MONEY TO BALANCE""")
            option = int(input("Enter option: "))
            if option == 1:
                self.get_goals()
            elif option == 2:
                self.get_recurring()
            elif option == 3:
                self.get_status()
            elif option == 4:
                goal_chosen = str(input("Enter name of goal: "))
                to_contribute = None
                if self.goals:
                    for goal in self.goals:
                        if goal.get_info()["name"] == goal_chosen:
                            to_contribute = goal
                    if not to_contribute:
                        print("Goal not found")
                    valid = False
                    while not valid:
                        amount = int(input("How much to contribute? "))
                        if amount >= 0:
                            valid = True
                            to_contribute.contribute(amount)
                            self.balance -= amount
                            print(f"Contributed {amount} to {goal.get_info()["name"]}")
                            self.expenses.append(amount)
                    self.goals = [goal for goal in self.goals if not goal.get_info()["completed"]]
            elif option == 5:
                if not self.recurring:
                    print("No recurring available")
                    return
                for rec in self.recurring:
                    info = rec.get_info()
                    if info["initial"] + timedelta(days=info["frequency"]) <= self.today:
                        if rec.get_info()["type"] == "expense":
                            self.balance -= info["amount"]
                            self.expenses.append(info["amount"])
                        else:
                            self.balance += info["amount"]
                            self.incomes.append(info["amount"])
                        rec.initial_date += timedelta(days=info["frequency"])
                self.today = datetime.now()
            elif option == 6:
                name = str(input("Enter name of goal: "))
                amount = int(input("Enter amount: "))
                due_date = int(input("Enter due date: "))
                if due_date > 0 and amount > 0:
                    goal = Goal(name, amount, due_date)
                    self.goals.append(goal)
                    print("Goal added")
                    return
                print("Invalid input")
            elif option == 7:
                name = str(input("Enter name of recurring: "))
                amount = int(input("Enter amount: "))
                frequency = int(input("Enter frequency"))
                type = int(input("Enter transaction type (0 = expense, 1 = income"))
                if amount > 0 and frequency > 0 and type in [0, 1]:
                    rec = Recurring_Item(name, amount, frequency, transaction_type="expense" if type == 0 else "income")
                    self.recurring.append(rec)
                    print("Recurring added")
                    return
                print("Invalid input")
            elif option == 8:
                amount = int(input("Enter amount: "))
                if amount > 0:
                    self.balance += amount
                    self.incomes.append(amount)
                    print(f"Added {amount} to balance")
                    return
                print("Invalid amount")
    
    def get_status(self):
        print(f"Amount of goals: {len(self.goals)}, Amount of recurring: {len(self.recurring)}, Current balance: {self.balance}, Total incomes: {sum(self.incomes)}, Total expenses: {sum(self.expenses)}")
    def get_goals(self):
        if not self.goals:
            print("No goals available.")
            return
        else:
            for goal in self.goals:
                info = goal.get_info()
                print(f"Name: {info['name']}, Amount: {info['progress']}/{info['amount']}, Due date: {info['date']}")
    def get_recurring(self):
        if not self.recurring:
            print("No recurring available.")
            return
        else:
            for rec in self.recurring:
                info = rec.get_info()
                print(f"Name: {info['name']}, Amount: {info['amount']}, Frequency: {info['frequency']}")
    
if __name__ == "__main__":
    Main = Main()
    Main.Main()