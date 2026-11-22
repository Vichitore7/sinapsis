import random
from fractions import Fraction

import pytest

from app.fractions_engine import (SKILLS, Exercise, InvalidExercise, evaluate, generate_exercise,
                                  generate_transfer, hints, parse_answer, validate_exercise)


@pytest.mark.parametrize("raw,expected", [
    ("5/6", Fraction(5, 6)), (" 5 / 6 ", Fraction(5, 6)), ("1 1/2", Fraction(3, 2)),
    ("2", Fraction(2)), ("0.5", Fraction(1, 2)), ("0,25", Fraction(1, 4)), ("10/12", Fraction(5, 6)),
])
def test_parse(raw, expected):
    assert parse_answer(raw).value == expected


@pytest.mark.parametrize("raw", ["", "abc", "5/", "5/0", "cinco sextos", "5//6"])
def test_parse_invalid(raw):
    assert parse_answer(raw) is None


SUM = Exercise("suma_distinto_den", 1, 2, 1, 3)   # 1/2 + 1/3 = 5/6


@pytest.mark.parametrize("raw,correct,misc", [
    ("5/6", True, None),
    ("10/12", True, None),            # correcto sin simplificar
    ("2/5", False, "suma_num_y_den"),  # el error clásico del documento
    ("1/6", False, "multiplico"),
    ("2/6", False, "no_convirtio_numeradores"),
    ("6/5", False, "invertida"),
    ("4/6", False, "error_calculo"),
    ("1/2", False, "solo_una_fraccion"),
    ("5/7", False, "posible_dedo"),
    ("hola", False, "no_interpretable"),
])
def test_evaluate_sum(raw, correct, misc):
    ev = evaluate(SUM, raw)
    assert ev.correct is correct
    assert ev.misconception == misc


def test_not_simplified_flag():
    assert evaluate(SUM, "10/12").not_simplified
    assert not evaluate(SUM, "5/6").not_simplified


def test_same_denominator_classic_error():
    ex = Exercise("suma_mismo_den", 2, 7, 3, 7)
    assert evaluate(ex, "5/7").correct
    assert evaluate(ex, "5/14").misconception == "suma_num_y_den"


def test_equivalence():
    ex = Exercise("equivalencia", 2, 3, target_den=12)
    assert evaluate(ex, "8").correct
    assert evaluate(ex, "8/12").correct
    assert evaluate(ex, "11").misconception == "pensamiento_aditivo"
    assert evaluate(ex, "4").misconception == "solo_factor"
    assert evaluate(ex, "4/6").misconception == "denominador_distinto"


@pytest.mark.parametrize("ex", [
    Exercise("suma_distinto_den", 1, 2, 1, 2),      # mismo denominador
    Exercise("suma_mismo_den", 1, 2, 1, 3),         # distinto denominador
    Exercise("suma_distinto_den", 1, 0, 1, 3),      # denominador cero
    Exercise("suma_distinto_den", 5, 2, 1, 3),      # impropia
    Exercise("suma_distinto_den", 1, 11, 1, 12),    # denominador común 132, demasiado grande
    Exercise("equivalencia", 2, 3, target_den=10),  # 10 no es múltiplo de 3
    Exercise("nada", 1, 2),
])
def test_invalid_generated_problems_are_rejected(ex):
    with pytest.raises(InvalidExercise):
        validate_exercise(ex)


@pytest.mark.parametrize("skill", SKILLS)
def test_generator_always_valid(skill):
    rng = random.Random(42)
    for _ in range(300):
        ex = generate_exercise(skill, rng)
        validate_exercise(ex)
        assert evaluate(ex, f"{ex.answer.numerator}/{ex.answer.denominator}").correct or \
            (skill == "equivalencia")
        assert len(hints(ex)) == 4


def test_equivalence_generated_answer():
    rng = random.Random(1)
    for _ in range(100):
        ex = generate_exercise("equivalencia", rng)
        assert evaluate(ex, str(ex.a * ex.target_den // ex.b)).correct


def test_transfer_is_word_problem():
    ex = generate_transfer(random.Random(3))
    assert ex.story and f"{ex.a}/{ex.b}" in ex.story


def test_hints_never_leak_answer_before_last():
    rng = random.Random(7)
    for _ in range(100):
        ex = generate_exercise("suma_distinto_den", rng)
        ans = f"{ex.answer.numerator}/{ex.answer.denominator}"
        for h in hints(ex)[:-1]:
            assert ans not in h
