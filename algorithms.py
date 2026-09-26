#IMPORTS
import datetime
import random
import math
from udt import (
    Stack
)

class Goal_Allocator:
    def __init__(self, goals_list, available):
        self.goals_list = goals_list
        self.available = int(available)
    
    def allocate_budget(self):
        available = int(self.available * 100) #bug fix, forgot 0/1 only works with ints
        rows, column = len(self.goals_list)+1, available + 1
        all_combos = [[0] * column for x in range(rows)]
        # each section of a row of the table is goals, each section of a column is a budget
        targets = [int(goal.target * 100) for goal in self.goals_list]
        priorities = [goal.priority.value for goal in self.goals_list]

        for i in range(1, len(self.goals_list)+1):
            goal = self.goals_list[i-1]
            target = targets[i-1]
            priority = priorities[i-1]
            for b in range(available + 1):
                if target <= b:
                    all_combos[i][b] = max(priority + all_combos[i-1][b - target], all_combos[i-1][b])
                    #decide whether it's worth taking the current or previous value, based on how much priority it gives us
                else:
                    all_combos[i][b] = all_combos[i-1][b]
                    #too expensive
        selected_goals = []
        b = available
        for i in range(len(self.goals_list), 0, -1):
            #backtrack
            if all_combos[i][b] != all_combos[i-1][b]: #check if we contributed
                goal = self.goals_list[i-1]
                selected_goals.append(goal)
                b -= targets[i-1]
        remaining_budget = self.available
        for goal in selected_goals:
            amount_to_add = min(goal.target - goal.get_progress(), remaining_budget)
            goal.add_contribution(amount_to_add) #add the contribution to the goal
            remaining_budget -= amount_to_add
            #deducting what we spent from budget
        self.available = remaining_budget
        return self.available
    
    def quick_sort(self, goals=None):
        if goals is None:
            goals = self.goals_list
        if len(goals) <= 1:
            return goals
        pivot = goals[-1]
        left = [goal for goal in goals[:-1] if goal.priority.value >= pivot.priority.value]
        right = [goal for goal in goals[:-1] if goal.priority.value < pivot.priority.value]
        return self.quick_sort(left) + [pivot] + self.quick_sort(right)
    
    def greedy(self):
        self.goals_list = self.quick_sort()
        number_of_remaining_goals = len(self.goals_list)
        while self.available > 0.01:
            if number_of_remaining_goals == 0:
                break
            progress_made = False
            for goal in self.goals_list:
                if not(goal.get_completed()):
                    contribution = min(goal.target-goal.get_progress(), self.available / number_of_remaining_goals)
                    if contribution < 0.01:
                        continue
                    goal.add_contribution(contribution)
                    self.available -= contribution
                    progress_made = True
                    if goal.get_completed():
                        number_of_remaining_goals -= 1
            if not progress_made:
                break
        return self.available
    

class Predictor:
    
    def __init__(self, income_history, expense_history, savings_history):

        self.income_history = income_history
        self.expense_history = expense_history
        self.savings_history = savings_history
    
    def weighted_predictions(self, stack, weights):
        if len(weights) > stack.pointer + 1:
            return 0
        predicted_value = 0
        temp_stack = Stack()
        i = 1
        while i <= len(weights):
            value = stack.pop()
            predicted_value += value * weights[-i] #calculate weighted average
            temp_stack.push(value)
            i += 1
        while not temp_stack.is_empty():
            stack.push(temp_stack.pop())

        return predicted_value / sum(weights) #normalise the weights
    
    def monte_carlo(self, history, goal, passes):
        if not goal or len(history) < 2:
            return 0.0
        months_left = max(1, goal.days_left() // 30)  #always returns between one month or n months (days converted into months)
        count = 0
        mean = sum(history)/len(history)
        sub_mean = [(x - mean)**2 for x in history]
        standard_deviation = math.sqrt(sum(sub_mean)/len(sub_mean))
        for i in range(passes):
            savings = goal.get_progress() #how much money is already contributed and "saved" to that goal
            for j in range(months_left):
                savings += max(0, random.gauss(mean, standard_deviation)) #take the normal/gaussian distribution for more accurate predictions, predictions >= 0
                if savings >= goal.target:
                    count += 1
                    break
        return count / passes #probability of goal completions out of the amount of passes completed
    
    def goal_classify(self, goal, probability, available):
        progress = min(goal.get_progress() / max(goal.target, 1), 1.0) #normalise progress data
        print(goal.get_progress(), goal.target, "****")
        # Normalize days left (0 = overdue, 1 = just started)
        today = datetime.date.today()  # avoid division by zero
        days_remaining = (goal.deadline - today).days
        days_left = max(0, min(1, days_remaining / 30))
        available = min(max(0, available / max(goal.target, 1)), 1) #normalise available funds
        score = (progress + days_left + available + probability) / 4
        if score >= 0.7 or probability >= 0.7:
            print(progress, days_left, available)
            return 1 # "good"
        elif score < 0.7 and score >= 0.5:
            print(progress, days_left, available)
            return 0 # "small risk"
        else:
            print(progress, days_left, available)
            return -1 # "large risk"

