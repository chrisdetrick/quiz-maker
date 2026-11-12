from dataclasses import dataclass
import random
from typing import Any
from drafter import *

# Global constants (allowed)
CORRECT_FEEDBACK = "Correct!"   # also compared against state.feedback to see if the last answer was right
TITLE_COLOR = "#2c5aa0"         # blue used for page headings
GOOD_COLOR = "green"            # correct answers and success messages
BAD_COLOR = "red"               # incorrect answers and error messages

set_website_title("Quiz Maker")


@dataclass
class Term:
    """A single vocabulary term and its definition. Neither field changes after creation."""
    term: str
    definition: str


@dataclass
class State:
    """
    Holds everything the website needs to remember between pages.

    user_terms: every Term the user has added or imported.
    quiz_terms: the shuffled Terms for the current quiz (missed Terms are appended to the end).
    current_question: index in quiz_terms of the question being answered.
    score: number of questions answered correctly on the first try in the current quiz.
    feedback: text shown after answering ("" means the question is not answered yet).
    choices: the four answer choices (term names) for the current question.
    message: a one-time status or error message shown on the next page that displays it.
    missed: maps a term's name to how many times it was answered incorrectly in the current quiz.
    """
    user_terms: list[Term]
    quiz_terms: list[Term]
    current_question: int
    score: int
    feedback: str
    choices: list[str]
    message: str
    missed: dict[str, int]


# helper function
def term_exists(terms: list[Term], name: str) -> bool:
    """Return True if a Term with this name (ignoring upper/lower case) is already in terms."""
    for term in terms:
        if term.term.lower() == name.lower():
            return True
    return False


# helper function
def is_term_format_valid(term_input: str) -> bool:
    """
    Return True if term_input looks like 'Term - Definition'.

    The text must contain ' - ' exactly once, so that it can be split into a term and a definition.
    """
    if " - " not in term_input:
        return False

    hyphen_count = 0
    for index, char in enumerate(term_input):
        # (index > 0 added so that index - 1 never wraps around to the end of the string)
        if index > 0 and index != len(term_input) - 1:
            if char == '-' and term_input[index - 1] == " " and term_input[index + 1] == " ":
                hyphen_count += 1
    if hyphen_count >= 2:
        return False
    return True


# helper function
def shuffle_terms(terms: list[Term]) -> list[Term]:
    """Return a new, randomly ordered list containing the same Terms (the original is unchanged)."""
    shuffled_terms = random.sample(terms, len(terms))
    return shuffled_terms


# helper function
def create_question_choices(correct_term: Term, terms: list[Term]) -> list[str]:
    """
    Return a shuffled list of four term names: the correct one plus three random wrong ones.

    The wrong choices are picked from the other Terms in `terms` (the caller must make sure
    there are at least three other Terms).
    """
    wrong_options = []
    for t in terms:
        if t.term != correct_term.term:
            wrong_options.append(t.term)
    choices = random.sample(wrong_options, 3)
    choices.append(correct_term.term)
    # shuffle so the correct answer isn't always in the same position
    return random.sample(choices, len(choices))


# helper function
def take_message(state: State) -> str:
    """Return the pending one-time message from the state and clear it so it only shows once."""
    message = state.message
    state.message = ""
    return message


# helper function
def make_message_content(message: str) -> list:
    """
    Turn a message into page content: red if it starts with 'Error', green otherwise.

    Returns an empty list if there is no message, so the result can be added with +.
    """
    if message == "":
        return []
    if message.startswith("Error"):
        return [Div(bold(change_color(message, BAD_COLOR)))]
    return [Div(bold(change_color(message, GOOD_COLOR)))]


# helper function
def make_title(text: str, level: int = 1) -> Any:
    """Return a Header whose text is colored with the site's title color."""
    return change_color(Header(text, level), TITLE_COLOR)


@route
def index(state: State) -> Page:
    """Default route Drafter loads first; it simply shows the home page."""
    return home(state)


@route
def home(state: State) -> Page:
    """Home page: buttons to every other page at the top, then each term on its own line."""
    content = [
        make_title("Quiz Maker", 1),
        Div(Button("Add Term", add_term),
            Button("Import Terms", import_terms),
            Button("Export Terms", export_terms),
            Button("Remove Term", remove_term),
            Button("Take Quiz", start_quiz)),
        HorizontalRule()
    ]
    content = content + make_message_content(take_message(state))

    content.append(make_title("Your Terms (" + str(len(state.user_terms)) + ")", 2))
    if len(state.user_terms) == 0:
        content.append(Div(italic("You haven't added any terms yet.")))
    # Loop over the Term instances stored in the state; each Div is its own line
    count = 0
    for term in state.user_terms:
        count = count + 1
        content.append(Div(str(count) + ". ", bold(term.term), " - " + term.definition))
    return Page(state, content)


@route
def add_term(state: State) -> Page:
    """Add Term page: two text boxes for the term and its definition."""
    content = [
        make_title("Add Term", 1),
        Div(Button("Cancel", home)),
        HorizontalRule()
    ]
    content = content + make_message_content(take_message(state))
    content.append(Div(bold("Term:")))
    content.append(Div(TextBox("term", "")))
    content.append(Div(bold("Definition:")))
    content.append(Div(TextBox("definition", "")))
    content.append(LineBreak())
    content.append(Div(Button("Add Term", save_term)))
    return Page(state, content)


@route
def save_term(state: State, term: str, definition: str) -> Page:
    """
    Validate the Add Term form and, if it is valid, add a new Term to state.user_terms.

    The parameter names match the names of the TextBoxes on the Add Term page.
    """
    term = term.strip()
    definition = definition.strip()
    if term == "" or definition == "":
        state.message = "Error: the term and the definition cannot be empty. No term has been added."
        return add_term(state)
    # Reuses is_term_format_valid so a term/definition can't contain ' - ' (that would break import/export)
    if not is_term_format_valid(term + " - " + definition):
        state.message = "Error: the term and definition cannot contain ' - '. No term has been added."
        return add_term(state)
    if term_exists(state.user_terms, term):
        state.message = "Error: that term has already been added. No term has been added."
        return add_term(state)

    state.user_terms.append(Term(term, definition))
    state.message = "New term added! " + term + " - " + definition
    return home(state)


@route
def import_terms(state: State) -> Page:
    """Import Terms page: one big text area where the user pastes many 'Term - Definition' lines."""
    content = [
        make_title("Import Terms", 1),
        Div(Button("Cancel", home)),
        HorizontalRule()
    ]
    content = content + make_message_content(take_message(state))
    content.append(Div("Enter one term per line in the format: ", bold("Term - Definition")))
    # The TextArea is added directly to the page (not wrapped in a Div) so that no extra
    # whitespace gets placed inside the box. The LineBreak after it keeps the layout on separate lines.
    content.append(TextArea("import_text"))
    content.append(LineBreak())
    content.append(Div(Button("Import", save_import)))
    return Page(state, content)


@route
def save_import(state: State, import_text: str) -> Page:
    """
    Read each line of the text area, and add every line that is in the 'Term - Definition' format.

    Lines that are blank, badly formatted, or duplicates of an existing term are skipped.
    The parameter name matches the name of the TextArea on the Import Terms page.
    """
    added = 0
    skipped = 0
    # splitlines() splits a string into a list of its lines (works for any kind of line ending)
    for line in import_text.splitlines():
        line = line.strip()
        if line == "":
            continue
        if not is_term_format_valid(line):
            skipped += 1
            continue
        term, definition = line.split(" - ")
        term = term.strip()
        definition = definition.strip()
        if term == "" or definition == "" or term_exists(state.user_terms, term):
            skipped += 1
        else:
            state.user_terms.append(Term(term, definition))
            added += 1

    state.message = "Imported " + str(added) + " term(s). Skipped " + str(skipped) + " line(s)."
    if added == 0:
        # Nothing was imported, so show this as an error (red)
        state.message = "Error: " + state.message
    return home(state)


@route
def export_terms(state: State) -> Page:
    """Export Terms page: shows all terms as 'Term - Definition' lines the user can copy and save."""
    content = [
        make_title("Export Terms", 1),
        Div(Button("Home", home)),
        HorizontalRule()
    ]
    if len(state.user_terms) == 0:
        content.append(Div(italic("There are no terms to export!")))
        return Page(state, content)

    export_text = ""
    # Loop over the Term instances to combine them into one string
    for term in state.user_terms:
        export_text = export_text + term.term + " - " + term.definition + "\n"
    content.append(Div("Copy the text below and save it somewhere. You can paste it into 'Import Terms' next time."))
    # PreformattedText keeps the line breaks
    content.append(PreformattedText(export_text))
    return Page(state, content)


@route
def remove_term(state: State) -> Page:
    """Remove Term page: Cancel / Remove All buttons at the top, then each term with its own Remove button."""
    content: list[Any] = [make_title("Remove Term", 1)]
    if len(state.user_terms) == 0:
        content.append(Div(Button("Home", home)))
        content.append(HorizontalRule())
        content.append(Div(italic("You need to add a term before you can remove one!")))
        return Page(state, content)

    content.append(Div(Button("Cancel", home), Button("Remove All", remove_all)))
    content.append(HorizontalRule())

    # Loop over the Term instances; each Remove button comes BEFORE its term and passes the
    # term's position to delete_term.
    # Advanced technique: the dictionary {"index": index} tells Drafter to give delete_term a parameter
    # named 'index' with this value when the button is clicked.
    for index, term in enumerate(state.user_terms):
        content.append(Div(Button("Remove", delete_term, {"index": index}),
                           "  " + str(index + 1) + ". ", bold(term.term), " - " + term.definition))
    return Page(state, content)


@route
def delete_term(state: State, index: int) -> Page:
    """Remove the Term at position `index` from state.user_terms, then return to the home page."""
    if 0 <= index < len(state.user_terms):
        removed_term = state.user_terms[index].term
        state.user_terms.pop(index)
        state.message = removed_term + " successfully removed."
    else:
        state.message = "Error: invalid input. No term has been removed."
    return home(state)


@route
def remove_all(state: State) -> Page:
    """Remove every Term from state.user_terms, then return to the home page."""
    count = len(state.user_terms)
    state.user_terms.clear()
    state.message = "All " + str(count) + " term(s) successfully removed."
    return home(state)


@route
def start_quiz(state: State) -> Page:
    """
    Start a new quiz: shuffle the user's terms and reset the score, question number, feedback and missed terms.

    A quiz needs at least four terms (one correct answer plus three wrong choices).
    """
    if len(state.user_terms) < 4:
        state.message = "Error: you must add at least 4 terms before you can take a quiz."
        return home(state)

    state.quiz_terms = shuffle_terms(state.user_terms)
    state.current_question = 0
    state.score = 0
    state.feedback = ""
    state.missed = {}
    state.choices = create_question_choices(state.quiz_terms[0], state.user_terms)
    # Advanced technique: a route can call another route function and return the Page it makes
    return quiz(state)


@route
def quiz(state: State, choice: str = "") -> Page:
    """
    Show the current question (a definition and four term buttons).

    When a button is clicked, `choice` holds the clicked term and is checked against the correct term.
    The default value "" lets other routes call quiz(state) just to display the question.
    Only answers to questions in the first pass count toward the score; retries of missed
    questions (which sit after the original terms in quiz_terms) do not add points.
    Every incorrect answer (including retries) is counted in state.missed.
    """
    current_term = state.quiz_terms[state.current_question]
    is_retry = state.current_question >= len(state.user_terms)

    # Process the answer (only if the question hasn't been answered yet)
    if choice != "" and state.feedback == "":
        if choice == current_term.term:
            state.feedback = CORRECT_FEEDBACK
            if not is_retry:
                state.score += 1
        else:
            state.feedback = "Incorrect! The correct answer was: " + current_term.term
            if current_term.term in state.missed:
                state.missed[current_term.term] += 1
            else:
                state.missed[current_term.term] = 1

    content: list[Any] = [Div(Button("Quit", home))]
    if is_retry:
        content.append(make_title("Question " + str(state.current_question + 1) + " (retry)", 2))
    else:
        content.append(make_title("Question " + str(state.current_question + 1), 2))
    content.append(HorizontalRule())
    content.append(Div(bold(current_term.definition)))
    content.append(LineBreak())

    if state.feedback == "":
        # one button per line
        for option in state.choices:
            content.append(Div(Button(option, quiz, {"choice": option})))
    else:
        if state.feedback == CORRECT_FEEDBACK:
            content.append(Div(bold(change_color(state.feedback, GOOD_COLOR))))
        else:
            content.append(Div(bold(change_color(state.feedback, BAD_COLOR))))
        content.append(LineBreak())
        content.append(Div(Button("Next Question", next_question)))
    return Page(state, content)


@route
def next_question(state: State) -> Page:
    """
    Move on to the next question.

    If the last answer was incorrect, that Term is appended to the end of quiz_terms so it
    has to be attempted again. If no questions remain, the results page is shown.
    """
    if state.feedback == "":
        # The question hasn't been answered yet, so stay on it
        return quiz(state)

    if state.feedback != CORRECT_FEEDBACK:
        state.quiz_terms.append(state.quiz_terms[state.current_question])
    state.current_question += 1
    state.feedback = ""

    if state.current_question >= len(state.quiz_terms):
        return results(state)

    state.choices = create_question_choices(state.quiz_terms[state.current_question], state.user_terms)
    return quiz(state)


@route
def results(state: State) -> Page:
    """Show the final score (correct on the first try) and which terms were missed, and how many times."""
    content = [
        make_title("Quiz Complete!", 1),
        Div(Button("Home", home), Button("Take Quiz Again", start_quiz)),
        HorizontalRule()
    ]

    score_text = "Final Score: " + str(state.score) + "/" + str(len(state.user_terms))
    if state.score == len(state.user_terms):
        content.append(Div(bold(change_color(score_text, GOOD_COLOR))))
    else:
        content.append(Div(bold(score_text)))
    content.append(LineBreak())

    content.append(make_title("Missed Terms", 2))
    if len(state.missed) == 0:
        content.append(Div(bold(change_color("You didn't miss any terms. Great job!", GOOD_COLOR))))
    # Loop over the missed dictionary; .items() gives each key (term name) and its value (times missed)
    for term_name, times_missed in state.missed.items():
        if times_missed == 1:
            times_text = " - missed 1 time"
        else:
            times_text = " - missed " + str(times_missed) + " times"
        content.append(Div(bold(change_color(term_name, BAD_COLOR)), times_text))
    return Page(state, content)

set_site_information(
    author="Christopher Detrick",
    description="A study tool that lets you import vocabulary terms and take a shuffled multiple-choice quiz.",
    sources=["Claude"],
    planning=[],
    links=[]
)

start_server(State([], [], 0, 0, "", [], "", {}))
