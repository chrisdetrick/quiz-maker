from dataclasses import dataclass
import random
from typing import Any, Optional
from drafter import *
from bakery import assert_equal

# Global constants (allowed)
CORRECT_FEEDBACK = "Correct!"   # also compared against state.feedback to see if the last answer was right
TITLE_COLOR = "#2c5aa0"         # blue used for page headings
GOOD_COLOR = "green"            # correct answers and success messages
BAD_COLOR = "red"               # incorrect answers and error messages
TERM_SEPARATOR = " - "          # separates a term from its definition when importing/exporting
MIN_TERMS_FOR_QUIZ = 4          # one correct answer plus three wrong choices
NUMBER_OF_CHOICES = 4           # answer buttons shown per question

set_website_title("Quiz Maker")

# Advanced technique (not covered in the course): every Button below is given the NAME of its
# route as a string (for example Button("Home", "home")) instead of the route function itself.
# This lets a button point to a route that is defined LATER in the file, so that each route can be
# unit tested directly underneath it. Drafter treats a route's name and the route function the same way.


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
    answer_choices: the four answer choices (term names) for the current question.
    message: a one-time status or error message shown on the next page that displays it.
    missed_counts: maps a term's name to how many times it was answered incorrectly in the current quiz.
    """
    user_terms: list[Term]
    quiz_terms: list[Term]
    current_question: int
    score: int
    feedback: str
    answer_choices: list[str]
    message: str
    missed_counts: dict[str, int]


# ----------------------------------------------------------------------------------------
# Helpers used only by the unit tests
# (The tests below are plain assert_equal lines with no variables, so a few small helpers
# build the Terms and States they need.)
# ----------------------------------------------------------------------------------------

def make_test_terms() -> list[Term]:
    """Return a fresh list of four Terms to use in the unit tests."""
    return [Term("cat", "a small pet"), Term("dog", "a loyal pet"),
            Term("fish", "lives in water"), Term("bird", "can fly")]


def make_test_state(terms: list[Term]) -> State:
    """Return a fresh State holding the given terms, with every other field at its starting value."""
    return State(terms, [], 0, 0, "", [], "", {})


def make_quiz_state(current_question: int, quiz_terms: list[Term], feedback: str) -> State:
    """Return a State in the middle of a quiz over the four test terms, for the quiz unit tests."""
    return State(make_test_terms(), quiz_terms, current_question, 0, feedback,
                 ["cat", "dog", "fish", "bird"], "", {})


# ----------------------------------------------------------------------------------------
# Helper functions (logic)
# ----------------------------------------------------------------------------------------

def term_exists(terms: list[Term], name: str) -> bool:
    """Return True if a Term with this name (ignoring upper/lower case) is already in terms."""
    for existing_term in terms:
        if existing_term.term.lower() == name.lower():
            return True
    return False


assert_equal(term_exists(make_test_terms(), "cat"), True)
assert_equal(term_exists(make_test_terms(), "CAT"), True)
assert_equal(term_exists(make_test_terms(), "horse"), False)
assert_equal(term_exists([], "cat"), False)


def is_term_format_valid(term_input: str) -> bool:
    """
    Return True if term_input looks like 'Term - Definition'.

    The text must contain ' - ' exactly once, so that it can be split into a term and a definition.
    """
    if TERM_SEPARATOR not in term_input:
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


assert_equal(is_term_format_valid("cat - a small pet"), True)
assert_equal(is_term_format_valid("well-known - famous"), True)
assert_equal(is_term_format_valid("no separator here"), False)
assert_equal(is_term_format_valid("a - b - c"), False)
assert_equal(is_term_format_valid(""), False)


def shuffle_terms(terms: list[Term]) -> list[Term]:
    """
    Return a new, randomly ordered list containing the same Terms (the original is unchanged).

    The exact order is random, so it can't be unit tested directly; the tests only check
    that the length and the Terms stay the same.
    """
    shuffled_terms = random.sample(terms, len(terms))
    return shuffled_terms


assert_equal(len(shuffle_terms(make_test_terms())), 4)
assert_equal(term_exists(shuffle_terms(make_test_terms()), "cat"), True)
assert_equal(term_exists(shuffle_terms(make_test_terms()), "bird"), True)
assert_equal(shuffle_terms([]), [])


def create_question_choices(correct_term: Term, terms: list[Term]) -> list[str]:
    """
    Return a shuffled list of four term names: the correct one plus three random wrong ones.

    The wrong choices are picked from the other Terms in `terms` (the caller must make sure
    there are at least three other Terms). Because the result is random, the tests only check
    its length, that it holds the correct term, and that it has no duplicates.
    """
    wrong_options = []
    for candidate_term in terms:
        if candidate_term.term != correct_term.term:
            wrong_options.append(candidate_term.term)
    answer_options = random.sample(wrong_options, NUMBER_OF_CHOICES - 1)
    answer_options.append(correct_term.term)
    # shuffle so the correct answer isn't always in the same position
    return random.sample(answer_options, len(answer_options))


assert_equal(len(create_question_choices(make_test_terms()[0], make_test_terms())), 4)
assert_equal("cat" in create_question_choices(make_test_terms()[0], make_test_terms()), True)
assert_equal(len(set(create_question_choices(make_test_terms()[0], make_test_terms()))), 4)


def take_message(state: State) -> str:
    """Return the pending one-time message from the state and clear it so it only shows once."""
    pending_message = state.message
    state.message = ""
    return pending_message


def message_left_after_take(message: str) -> str:
    """Test helper: put message in a new State, call take_message on it, and return what is left."""
    message_state = make_test_state([])
    message_state.message = message
    take_message(message_state)
    return message_state.message


def taken_message(message: str) -> str:
    """Test helper: put message in a new State and return what take_message gives back."""
    message_state = make_test_state([])
    message_state.message = message
    return take_message(message_state)


assert_equal(taken_message("Hello"), "Hello")
assert_equal(taken_message(""), "")
assert_equal(message_left_after_take("Hello"), "")


def find_term_error(term_name: str, definition: str, terms: list[Term]) -> str:
    """
    Return an error message if this term/definition can't be added to terms, or "" if it is fine.

    A term can't be added if either part is empty, if either part contains ' - ' (that would
    break import/export), or if the term name already exists.
    """
    if term_name == "" or definition == "":
        return "Error: the term and the definition cannot be empty. No term has been added."
    # Reuses is_term_format_valid so a term/definition can't contain ' - '
    if not is_term_format_valid(term_name + TERM_SEPARATOR + definition):
        return "Error: the term and definition cannot contain ' - '. No term has been added."
    if term_exists(terms, term_name):
        return "Error: that term has already been added. No term has been added."
    return ""


assert_equal(find_term_error("horse", "an animal", make_test_terms()), "")
assert_equal(find_term_error("", "an animal", make_test_terms()).startswith("Error"), True)
assert_equal(find_term_error("horse", "", make_test_terms()).startswith("Error"), True)
assert_equal(find_term_error("a - b", "an animal", make_test_terms()).startswith("Error"), True)
assert_equal(find_term_error("cat", "another one", make_test_terms()).startswith("Error"), True)


def parse_term_line(line: str) -> Optional[Term]:
    """
    Turn one line of 'Term - Definition' text into a Term.

    Return None if the line is in the wrong format or if the term or definition is empty.
    """
    stripped_line = line.strip()
    if not is_term_format_valid(stripped_line):
        return None
    # the second argument (1) means "split at most once"
    term_name, definition = stripped_line.split(TERM_SEPARATOR, 1)
    term_name = term_name.strip()
    definition = definition.strip()
    if term_name == "" or definition == "":
        return None
    return Term(term_name, definition)


assert_equal(parse_term_line("cat - a small pet"), Term("cat", "a small pet"))
assert_equal(parse_term_line("  cat  -  a small pet  "), Term("cat", "a small pet"))
assert_equal(parse_term_line("not a term line"), None)
assert_equal(parse_term_line("cat - a - b"), None)
assert_equal(parse_term_line(" - missing term"), None)


def import_lines(import_text: str, terms: list[Term]) -> tuple[int, int]:
    """
    Add every valid, non-duplicate 'Term - Definition' line in import_text to terms.

    Blank lines are ignored. Return (number of terms added, number of lines skipped).
    """
    added_count = 0
    skipped_count = 0
    # splitlines() splits a string into a list of its lines (works for any kind of line ending)
    for line in import_text.splitlines():
        if line.strip() == "":
            continue
        parsed_term = parse_term_line(line)
        if parsed_term is None or term_exists(terms, parsed_term.term):
            skipped_count += 1
        else:
            terms.append(parsed_term)
            added_count += 1
    return added_count, skipped_count


def terms_after_import(import_text: str, terms: list[Term]) -> list[Term]:
    """Test helper: run import_lines on terms and return the list of terms afterwards."""
    import_lines(import_text, terms)
    return terms


assert_equal(import_lines("dog - a loyal pet\n\nbad line\ncat - duplicate\nfish - lives in water",
                          [Term("cat", "a small pet")]), (2, 2))
assert_equal(import_lines("", []), (0, 0))
assert_equal(terms_after_import("dog - a loyal pet\n\nbad line\ncat - duplicate\nfish - lives in water",
                                [Term("cat", "a small pet")]),
             [Term("cat", "a small pet"), Term("dog", "a loyal pet"), Term("fish", "lives in water")])


def make_import_message(added_count: int, skipped_count: int) -> str:
    """Return the message shown after an import (starts with 'Error' if nothing was added)."""
    message = "Imported " + str(added_count) + " term(s). Skipped " + str(skipped_count) + " line(s)."
    if added_count == 0:
        return "Error: " + message
    return message


assert_equal(make_import_message(2, 1), "Imported 2 term(s). Skipped 1 line(s).")
assert_equal(make_import_message(0, 3), "Error: Imported 0 term(s). Skipped 3 line(s).")


def build_export_text(terms: list[Term]) -> str:
    """Return all terms as 'Term - Definition' lines, one per line, ready to be imported again."""
    export_text = ""
    # Loop over the Term instances to combine them into one string
    for term in terms:
        export_text = export_text + term.term + TERM_SEPARATOR + term.definition + "\n"
    return export_text


assert_equal(build_export_text([]), "")
assert_equal(build_export_text([Term("cat", "a small pet"), Term("dog", "a loyal pet")]),
             "cat - a small pet\ndog - a loyal pet\n")


def record_missed_term(missed_counts: dict[str, int], term_name: str) -> None:
    """Add one to the number of times term_name was missed (starting at 1 the first time)."""
    if term_name in missed_counts:
        missed_counts[term_name] += 1
    else:
        missed_counts[term_name] = 1


def missed_counts_after_records(term_names: list[str]) -> dict[str, int]:
    """Test helper: call record_missed_term for each name in order and return the resulting dictionary."""
    missed_counts: dict[str, int] = {}
    for term_name in term_names:
        record_missed_term(missed_counts, term_name)
    return missed_counts


assert_equal(missed_counts_after_records([]), {})
assert_equal(missed_counts_after_records(["cat"]), {"cat": 1})
assert_equal(missed_counts_after_records(["cat", "dog", "cat"]), {"cat": 2, "dog": 1})


def is_retry_question(state: State) -> bool:
    """
    Return True if the current question is a retry of a missed question.

    Retries are appended after the original terms, so their position is at or past len(user_terms).
    """
    return state.current_question >= len(state.user_terms)


assert_equal(is_retry_question(make_quiz_state(3, make_test_terms(), "")), False)
assert_equal(is_retry_question(make_quiz_state(4, make_test_terms(), "")), True)


def process_answer(state: State, chosen_term: str) -> None:
    """
    Check chosen_term against the current question and update feedback, score and missed_counts.

    Does nothing if no term was chosen or the question was already answered. Only first-pass
    questions add to the score; every incorrect answer (including retries) is recorded as missed.
    """
    if chosen_term == "" or state.feedback != "":
        return
    correct_term = state.quiz_terms[state.current_question]
    if chosen_term == correct_term.term:
        state.feedback = CORRECT_FEEDBACK
        if not is_retry_question(state):
            state.score += 1
    else:
        state.feedback = "Incorrect! The correct answer was: " + correct_term.term
        record_missed_term(state.missed_counts, correct_term.term)


def state_after_answer(current_question: int, quiz_terms: list[Term], feedback: str,
                       chosen_term: str) -> State:
    """Test helper: build a quiz State, call process_answer on it, and return the State afterwards."""
    answer_state = make_quiz_state(current_question, quiz_terms, feedback)
    process_answer(answer_state, chosen_term)
    return answer_state


assert_equal(state_after_answer(0, make_test_terms(), "", "cat").feedback, CORRECT_FEEDBACK)
assert_equal(state_after_answer(0, make_test_terms(), "", "cat").score, 1)
assert_equal(state_after_answer(0, make_test_terms(), "", "dog").feedback,
             "Incorrect! The correct answer was: cat")
assert_equal(state_after_answer(0, make_test_terms(), "", "dog").score, 0)
assert_equal(state_after_answer(0, make_test_terms(), "", "dog").missed_counts, {"cat": 1})
# already answered: nothing changes
assert_equal(state_after_answer(0, make_test_terms(), CORRECT_FEEDBACK, "cat").score, 0)
# no choice made: nothing changes
assert_equal(state_after_answer(0, make_test_terms(), "", "").feedback, "")
# a retry (position 4 is past the four original terms) is correct but doesn't add to the score
assert_equal(state_after_answer(4, make_test_terms() + [Term("cat", "a small pet")], "", "cat").feedback,
             CORRECT_FEEDBACK)
assert_equal(state_after_answer(4, make_test_terms() + [Term("cat", "a small pet")], "", "cat").score, 0)


def describe_times_missed(times_missed: int) -> str:
    """Return text like ' - missed 1 time' or ' - missed 3 times'."""
    if times_missed == 1:
        return " - missed 1 time"
    return " - missed " + str(times_missed) + " times"


assert_equal(describe_times_missed(1), " - missed 1 time")
assert_equal(describe_times_missed(3), " - missed 3 times")


# ----------------------------------------------------------------------------------------
# Helper functions (page components)
# ----------------------------------------------------------------------------------------

def make_title(text: str, level: int = 1) -> Any:
    """
    Return a Header whose text is colored with the site's title color.

    Can't be unit tested: it only builds a styled Drafter component, so it is checked by running the site.
    """
    return change_color(Header(text, level), TITLE_COLOR)


def make_message_content(message: str) -> list[Any]:
    """
    Turn a message into page content: red if it starts with 'Error', green otherwise.

    Returns an empty list if there is no message, so the result can be added to a page's content.
    (Only the length of the result is unit tested, since the styled components can't be compared.)
    """
    if message == "":
        return []
    if message.startswith("Error"):
        return [Div(bold(change_color(message, BAD_COLOR)))]
    return [Div(bold(change_color(message, GOOD_COLOR)))]


assert_equal(make_message_content(""), [])
assert_equal(len(make_message_content("Success")), 1)
assert_equal(len(make_message_content("Error: bad")), 1)


def make_term_line(term_number: int, term: Term) -> Any:
    """
    Return a Div showing '1. Term - Definition' (with the term in bold) on its own line.

    Can't be unit tested: it only builds Drafter components, so it is checked by running the site.
    """
    return Div(str(term_number) + ". ", bold(term.term), TERM_SEPARATOR + term.definition)


def make_removal_row(term_index: int, term: Term) -> Any:
    """
    Return a Div with a Remove button (placed before the term) for the Term at term_index.

    Can't be unit tested: it only builds Drafter components, so it is checked by running the site.
    """
    return Div(Button("Remove", "delete_term", {"term_index": term_index}),
               "  " + str(term_index + 1) + ". ", bold(term.term), TERM_SEPARATOR + term.definition)


def make_choice_buttons(answer_choices: list[str]) -> list[Any]:
    """
    Return one Div per answer choice, each holding a button that submits that choice.

    Can't be unit tested: it only builds Drafter components, so it is checked by running the site.
    """
    choice_buttons = []
    for answer_choice in answer_choices:
        choice_buttons.append(Div(Button(answer_choice, "quiz", {"chosen_term": answer_choice})))
    return choice_buttons


def make_feedback_component(feedback: str) -> Any:
    """
    Return the feedback text in bold: green if it is the correct message, red otherwise.

    Can't be unit tested: it only builds styled Drafter components, so it is checked by running the site.
    """
    if feedback == CORRECT_FEEDBACK:
        return Div(bold(change_color(feedback, GOOD_COLOR)))
    return Div(bold(change_color(feedback, BAD_COLOR)))


def make_missed_content(missed_counts: dict[str, int]) -> list[Any]:
    """
    Return one red line per missed term, or a green message if no terms were missed.

    Can't be unit tested: it only builds styled Drafter components, so it is checked by running the site.
    """
    if len(missed_counts) == 0:
        return [Div(bold(change_color("You didn't miss any terms. Great job!", GOOD_COLOR)))]
    missed_content = []
    # Loop over the dictionary; .items() gives each key (term name) and its value (times missed)
    for term_name, times_missed in missed_counts.items():
        missed_content.append(Div(bold(change_color(term_name, BAD_COLOR)),
                                  describe_times_missed(times_missed)))
    return missed_content


# ----------------------------------------------------------------------------------------
# Routes
# (The route tests check the state inside the returned Page. Routes call take_message, so a
# message set before a page is shown is cleared afterwards. Routes are ordered so that each
# route only calls routes that are defined above it.)
# ----------------------------------------------------------------------------------------

@route
def home(state: State) -> Page:
    """Home page: buttons to every other page at the top, then each term on its own line."""
    page_content: list[Any] = [
        make_title("Quiz Maker", 1),
        Div(Button("Add Term", "add_term"),
            Button("Import Terms", "import_terms"),
            Button("Export Terms", "export_terms"),
            Button("Remove Term", "remove_term"),
            Button("Take Quiz", "start_quiz")),
        HorizontalRule()
    ]
    page_content.extend(make_message_content(take_message(state)))

    page_content.append(make_title("Your Terms (" + str(len(state.user_terms)) + ")", 2))
    if len(state.user_terms) == 0:
        page_content.append(Div(italic("You haven't added any terms yet.")))
    # Loop over the Term instances stored in the state; each Div is its own line
    term_number = 0
    for term in state.user_terms:
        term_number = term_number + 1
        page_content.append(make_term_line(term_number, term))
    return Page(state, page_content)


def make_home_test_state() -> State:
    """Test helper: return a State with four terms and a pending message, for testing home."""
    home_state = make_test_state(make_test_terms())
    home_state.message = "Some message"
    return home_state


assert_equal(home(make_home_test_state()).state, make_test_state(make_test_terms()))
assert_equal(home(make_test_state([])).state, make_test_state([]))


@route
def index(state: State) -> Page:
    """Default route Drafter loads first; it simply shows the home page."""
    return home(state)


assert_equal(index(make_test_state(make_test_terms())).state, make_test_state(make_test_terms()))


@route
def add_term(state: State) -> Page:
    """Add Term page: two text boxes for the term and its definition."""
    page_content: list[Any] = [
        make_title("Add Term", 1),
        Div(Button("Cancel", "home")),
        HorizontalRule()
    ]
    page_content.extend(make_message_content(take_message(state)))
    page_content.append(Div(bold("Term:")))
    page_content.append(Div(TextBox("new_term", "")))
    page_content.append(Div(bold("Definition:")))
    page_content.append(Div(TextBox("new_definition", "")))
    page_content.append(LineBreak())
    page_content.append(Div(Button("Add Term", "save_term")))
    return Page(state, page_content)


def make_add_term_test_state() -> State:
    """Test helper: return an empty State with a pending error message, for testing add_term."""
    add_term_state = make_test_state([])
    add_term_state.message = "Error: something"
    return add_term_state


assert_equal(add_term(make_add_term_test_state()).state, make_test_state([]))


@route
def save_term(state: State, new_term: str, new_definition: str) -> Page:
    """
    Validate the Add Term form and, if it is valid, add a new Term to state.user_terms.

    The parameter names match the names of the TextBoxes on the Add Term page.
    """
    term_name = new_term.strip()
    definition = new_definition.strip()
    error_message = find_term_error(term_name, definition, state.user_terms)
    if error_message != "":
        state.message = error_message
        return add_term(state)

    state.user_terms.append(Term(term_name, definition))
    state.message = "New term added! " + term_name + TERM_SEPARATOR + definition
    return home(state)


assert_equal(save_term(make_test_state([]), "  cat ", " a small pet ").state.user_terms,
             [Term("cat", "a small pet")])
assert_equal(save_term(make_test_state([]), "", "a small pet").state.user_terms, [])
assert_equal(save_term(make_test_state(make_test_terms()), "cat", "duplicate").state.user_terms,
             make_test_terms())


@route
def import_terms(state: State) -> Page:
    """Import Terms page: one big text area where the user pastes many 'Term - Definition' lines."""
    page_content: list[Any] = [
        make_title("Import Terms", 1),
        Div(Button("Cancel", "home")),
        HorizontalRule()
    ]
    page_content.extend(make_message_content(take_message(state)))
    page_content.append(Div("Enter one term per line in the format: ", bold("Term - Definition")))
    # The TextArea is added directly to the page (not wrapped in a Div) so that no extra
    # whitespace gets placed inside the box. The LineBreak after it keeps the layout on separate lines.
    page_content.append(TextArea("import_text"))
    page_content.append(LineBreak())
    page_content.append(Div(Button("Import", "save_import")))
    return Page(state, page_content)


assert_equal(import_terms(make_test_state(make_test_terms())).state, make_test_state(make_test_terms()))


@route
def save_import(state: State, import_text: str) -> Page:
    """
    Add every line of the text area that is in the 'Term - Definition' format, then show the home page.

    Lines that are blank, badly formatted, or duplicates of an existing term are skipped.
    The parameter name matches the name of the TextArea on the Import Terms page.
    """
    added_count, skipped_count = import_lines(import_text, state.user_terms)
    state.message = make_import_message(added_count, skipped_count)
    return home(state)


assert_equal(save_import(make_test_state([]), "cat - a small pet\nbad line\ndog - a loyal pet").state.user_terms,
             [Term("cat", "a small pet"), Term("dog", "a loyal pet")])
assert_equal(save_import(make_test_state([]), "bad line").state.user_terms, [])


@route
def export_terms(state: State) -> Page:
    """Export Terms page: shows all terms as 'Term - Definition' lines the user can copy and save."""
    page_content: list[Any] = [
        make_title("Export Terms", 1),
        Div(Button("Home", "home")),
        HorizontalRule()
    ]
    if len(state.user_terms) == 0:
        page_content.append(Div(italic("There are no terms to export!")))
        return Page(state, page_content)

    page_content.append(Div("Copy the text below and save it somewhere. "
                            "You can paste it into 'Import Terms' next time."))
    # PreformattedText keeps the line breaks
    page_content.append(PreformattedText(build_export_text(state.user_terms)))
    return Page(state, page_content)


assert_equal(export_terms(make_test_state(make_test_terms())).state, make_test_state(make_test_terms()))
assert_equal(export_terms(make_test_state([])).state, make_test_state([]))


@route
def remove_term(state: State) -> Page:
    """Remove Term page: Cancel / Remove All buttons at the top, then each term with its own Remove button."""
    page_content: list[Any] = [make_title("Remove Term", 1)]
    if len(state.user_terms) == 0:
        page_content.append(Div(Button("Home", "home")))
        page_content.append(HorizontalRule())
        page_content.append(Div(italic("You need to add a term before you can remove one!")))
        return Page(state, page_content)

    page_content.append(Div(Button("Cancel", "home"), Button("Remove All", "remove_all")))
    page_content.append(HorizontalRule())

    # Loop over the Term instances; each Remove button comes BEFORE its term.
    # Advanced technique: in make_removal_row, the dictionary {"term_index": term_index} tells Drafter
    # to give delete_term a parameter named 'term_index' with this value when the button is clicked.
    for term_index, term in enumerate(state.user_terms):
        page_content.append(make_removal_row(term_index, term))
    return Page(state, page_content)


assert_equal(remove_term(make_test_state(make_test_terms())).state, make_test_state(make_test_terms()))
assert_equal(remove_term(make_test_state([])).state, make_test_state([]))


@route
def delete_term(state: State, term_index: int) -> Page:
    """Remove the Term at position `term_index` from state.user_terms, then return to the home page."""
    if 0 <= term_index < len(state.user_terms):
        removed_term = state.user_terms[term_index].term
        state.user_terms.pop(term_index)
        state.message = removed_term + " successfully removed."
    else:
        state.message = "Error: invalid input. No term has been removed."
    return home(state)


assert_equal(delete_term(make_test_state(make_test_terms()), 1).state.user_terms,
             [Term("cat", "a small pet"), Term("fish", "lives in water"), Term("bird", "can fly")])
assert_equal(delete_term(make_test_state(make_test_terms()), 10).state.user_terms, make_test_terms())
assert_equal(delete_term(make_test_state(make_test_terms()), -1).state.user_terms, make_test_terms())


@route
def remove_all(state: State) -> Page:
    """Remove every Term from state.user_terms, then return to the home page."""
    removed_count = len(state.user_terms)
    state.user_terms.clear()
    state.message = "All " + str(removed_count) + " term(s) successfully removed."
    return home(state)


assert_equal(remove_all(make_test_state(make_test_terms())).state.user_terms, [])
assert_equal(remove_all(make_test_state([])).state.user_terms, [])


@route
def quiz(state: State, chosen_term: str = "") -> Page:
    """
    Show the current question (a definition and four term buttons) and process the user's answer.

    When a button is clicked, `chosen_term` holds the clicked term and is checked against the
    correct term. The default value "" lets other routes call quiz(state) just to display the question.
    """
    process_answer(state, chosen_term)
    current_term = state.quiz_terms[state.current_question]

    page_content: list[Any] = [Div(Button("Quit", "home"))]
    question_title = "Question " + str(state.current_question + 1)
    if is_retry_question(state):
        question_title = question_title + " (retry)"
    page_content.append(make_title(question_title, 2))
    page_content.append(HorizontalRule())
    page_content.append(Div(bold(current_term.definition)))
    page_content.append(LineBreak())

    if state.feedback == "":
        # one button per line
        page_content.extend(make_choice_buttons(state.answer_choices))
    else:
        page_content.append(make_feedback_component(state.feedback))
        page_content.append(LineBreak())
        page_content.append(Div(Button("Next Question", "next_question")))
    return Page(state, page_content)


assert_equal(quiz(make_quiz_state(0, make_test_terms(), "")).state, make_quiz_state(0, make_test_terms(), ""))
assert_equal(quiz(make_quiz_state(0, make_test_terms(), ""), "cat").state.score, 1)
assert_equal(quiz(make_quiz_state(0, make_test_terms(), ""), "dog").state.score, 0)
assert_equal(quiz(make_quiz_state(0, make_test_terms(), ""), "dog").state.missed_counts, {"cat": 1})


@route
def results(state: State) -> Page:
    """Show the final score (correct on the first try) and which terms were missed, and how many times."""
    page_content: list[Any] = [
        make_title("Quiz Complete!", 1),
        Div(Button("Home", "home"), Button("Take Quiz Again", "start_quiz")),
        HorizontalRule()
    ]

    score_text = "Final Score: " + str(state.score) + "/" + str(len(state.user_terms))
    if state.score == len(state.user_terms):
        page_content.append(Div(bold(change_color(score_text, GOOD_COLOR))))
    else:
        page_content.append(Div(bold(score_text)))
    page_content.append(LineBreak())

    page_content.append(make_title("Missed Terms", 2))
    page_content.extend(make_missed_content(state.missed_counts))
    return Page(state, page_content)


def make_finished_quiz_state() -> State:
    """Test helper: return a State at the end of a quiz with a score of 3 and cat missed twice."""
    finished_quiz_state = make_quiz_state(4, make_test_terms(), "")
    finished_quiz_state.score = 3
    finished_quiz_state.missed_counts = {"cat": 2}
    return finished_quiz_state


assert_equal(results(make_finished_quiz_state()).state.score, 3)
assert_equal(results(make_finished_quiz_state()).state.missed_counts, {"cat": 2})


@route
def start_quiz(state: State) -> Page:
    """
    Start a new quiz: shuffle the user's terms and reset the score, question number, feedback and missed terms.

    A quiz needs at least four terms. Because the shuffle is random, only the "not enough terms"
    case and the properties of the new quiz (not its exact order) are unit tested.
    """
    if len(state.user_terms) < MIN_TERMS_FOR_QUIZ:
        state.message = "Error: you must add at least 4 terms before you can take a quiz."
        return home(state)

    state.quiz_terms = shuffle_terms(state.user_terms)
    state.current_question = 0
    state.score = 0
    state.feedback = ""
    state.missed_counts = {}
    state.answer_choices = create_question_choices(state.quiz_terms[0], state.user_terms)
    # Advanced technique: a route can call another route function and return the Page it makes
    return quiz(state)


def first_answer_is_in_choices() -> bool:
    """Test helper: start a quiz and return True if the first question's correct term is a choice."""
    started_state = start_quiz(make_test_state(make_test_terms())).state
    return started_state.quiz_terms[0].term in started_state.answer_choices


assert_equal(start_quiz(make_test_state(make_test_terms()[:3])).state.quiz_terms, [])
assert_equal(len(start_quiz(make_test_state(make_test_terms())).state.quiz_terms), 4)
assert_equal(start_quiz(make_test_state(make_test_terms())).state.current_question, 0)
assert_equal(start_quiz(make_test_state(make_test_terms())).state.score, 0)
assert_equal(start_quiz(make_test_state(make_test_terms())).state.feedback, "")
assert_equal(start_quiz(make_test_state(make_test_terms())).state.missed_counts, {})
assert_equal(len(start_quiz(make_test_state(make_test_terms())).state.answer_choices), 4)
assert_equal(first_answer_is_in_choices(), True)


@route
def next_question(state: State) -> Page:
    """
    Move on to the next question.

    If the last answer was incorrect, that Term is appended to the end of quiz_terms so it
    has to be attempted again. If no questions remain, the results page is shown. The answer
    choices for the next question are random, so the tests only check how many there are.
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

    state.answer_choices = create_question_choices(state.quiz_terms[state.current_question],
                                                   state.user_terms)
    return quiz(state)


# unanswered question: nothing changes
assert_equal(next_question(make_quiz_state(0, make_test_terms(), "")).state,
             make_quiz_state(0, make_test_terms(), ""))
# correct answer on the last question: the quiz ends and no question is added
assert_equal(next_question(make_quiz_state(3, make_test_terms(), CORRECT_FEEDBACK)).state.current_question, 4)
assert_equal(len(next_question(make_quiz_state(3, make_test_terms(), CORRECT_FEEDBACK)).state.quiz_terms), 4)
# incorrect answer: the missed term is added to the end and the next question is shown
assert_equal(next_question(make_quiz_state(0, make_test_terms(), "Incorrect! ...")).state.current_question, 1)
assert_equal(len(next_question(make_quiz_state(0, make_test_terms(), "Incorrect! ...")).state.quiz_terms), 5)
assert_equal(next_question(make_quiz_state(0, make_test_terms(), "Incorrect! ...")).state.quiz_terms[4],
             Term("cat", "a small pet"))
assert_equal(next_question(make_quiz_state(0, make_test_terms(), "Incorrect! ...")).state.feedback, "")
assert_equal(len(next_question(make_quiz_state(0, make_test_terms(), "Incorrect! ...")).state.answer_choices), 4)
# incorrect answer on the last original question: the missed term is retried
assert_equal(next_question(make_quiz_state(3, make_test_terms(), "Incorrect! ...")).state.current_question, 4)
assert_equal(len(next_question(make_quiz_state(3, make_test_terms(), "Incorrect! ...")).state.quiz_terms), 5)


set_site_information(
    author="Christopher Detrick",
    description="A study tool that lets you import vocabulary terms and take a shuffled multiple-choice quiz.",
    sources=["Claude"],
    planning=[],
    links=[]
)

start_server(State([], [], 0, 0, "", [], "", {}))
