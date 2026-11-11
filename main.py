from dataclasses import dataclass
import random
from drafter import *

@dataclass
class Term:
    term: str
    definition: str
    
user_terms = []
quiz_question_choices = []

# helper function
def find_removal_options(terms: list[Term]) -> list[str]:
    removal_options = []
    count = 0
    for term in terms:
        count = count + 1
        removal_options.append(str(count))
    return removal_options

# helper function
def is_term_format_valid(term_input: str) -> bool:
    if " - " not in term_input:
        return False
    
    hyphen_count = 0
    for index, char in enumerate(term_input):
        if index != len(term_input) - 1:
            if char == '-' and term_input[index - 1] == " " and term_input[index + 1] == " ":
                hyphen_count += 1
    if hyphen_count >= 2:
        return False
    return True

# helper function
def shuffle_terms(terms: list[Term]) -> list[Term]:
    shuffled_terms = random.sample(terms, len(terms))
    return shuffled_terms

# helper function, called by create_question_choices()
def determine_answer_choice_odds(terms: list[Term]) -> float:
    # determines the odds that each term in the list has of being one of the four answer choices in a question
    odds = 4 / len(terms)
    return odds


# helper function
def create_question_choices(terms: list[Term]):
    odds = determine_answer_choice_odds(terms)
    for index, term in enumerate(terms):
        single_question_choices = [term.term]
        while len(single_question_choices) < 4:
            for t in terms:
                if len(single_question_choices) < 4:
                    if random.random() < odds and t.term not in single_question_choices:
                        single_question_choices.append(t.term)
        #shuffle
        single_question_choices = random.sample(single_question_choices, len(single_question_choices))
        quiz_question_choices.append(single_question_choices)


# helper function
def present_question(correct_term: Term, all_terms: list[Term], 
                    term_number: int, answer_choices: list[str]) -> bool:
    
    user_guess = 0
    print("\nQ" + str(term_number) + ": " + correct_term.definition + "\n" +
          "\t1| " + answer_choices[0] + "\n" +
          "\t2| " + answer_choices[1] + "\n" +
          "\t3| " + answer_choices[2] + "\n" +
          "\t4| " + answer_choices[3])
    while user_guess not in ['1','2','3','4']:
        user_guess = input("Type a number 1-4 to guess an option!\n")
    user_guess = int(user_guess)
    term_guessed = answer_choices[user_guess - 1]
    if term_guessed == correct_term.term:
        return True
    else:
        return False



def add_term():
    term_input = input("Enter a term and definition in the following format: Term - Definition\n")
    if is_term_format_valid(term_input) == False:
        print("Invalid format. No term has been added.")
        return
    term, definition = term_input.split(" - ")
    new_term = Term(term, definition)
    user_terms.append(new_term)
    print("New term added!\n\tTerm: " + term + "\n\tDefinition: " + definition)

def take_quiz():
    if len(user_terms) < 4:
        print("You must add at least 4 terms before you can take a quiz.")
        return
    
    quiz_question_choices.clear()
    shuffled_terms = shuffle_terms(user_terms)
    create_question_choices(shuffled_terms)
    score = 0
    
    for term_index, term in enumerate(shuffled_terms):
        is_q_answer_correct = present_question(term, shuffled_terms, term_index + 1,
                                            quiz_question_choices[term_index])
        if is_q_answer_correct == True:
            score += 1
            print("\nCorrect!")
        elif is_q_answer_correct == False:
            print("\nIncorrect!")
    print("Final Score: " + str(score) + "/" + str(len(shuffled_terms)))

def view_terms():
    if len(user_terms) == 0:
        print("There are no terms to view!")
        return
    count = 0
    for term in user_terms:
        count = count + 1
        print(str(count) + ": " + term.term + " - " + term.definition)

def remove_term():
    if len(user_terms) == 0:
        print("You need to add a term before you can remove one!")
        return
    removal_options = find_removal_options(user_terms)
    view_terms()
    user_input = input("Type a number to remove that term.\n")
    if user_input in removal_options:
        index_to_remove = int(user_input) - 1
        removed_term = user_terms[index_to_remove].term
        user_terms.pop(index_to_remove)
        print(removed_term + " successfully removed.")
    else:
        print("Invalid input. No term has been removed.")

def main():
    while True:
        user_input = input("\n- Type 'a' to add a term.\n- Type 'q' to take a multiple choice quiz." +
                           "\n- Type 'v' to view all terms.\n- Type 'r' to remove a term.\n")
        if user_input == 'a':
            add_term()
        if user_input == 'q':
            take_quiz()
        if user_input == 'v':
            view_terms()
        if user_input == 'r':
            remove_term()
        
main()

@route
def index(state: State) -> Page:
    return Page(state, ["Hello World!"])

start_server(State())
