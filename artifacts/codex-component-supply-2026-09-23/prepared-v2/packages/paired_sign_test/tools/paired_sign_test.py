import hashlib
import json
import math
import re
import sys
from decimal import Decimal, InvalidOperation


def need(value):
    if not value:
        raise ValueError("invalid input")


def obj(value, keys):
    need(type(value) is dict and set(value) == set(keys))


def text(value, minimum=0, maximum=2048):
    need(type(value) is str and minimum <= len(value) <= maximum)
    value.encode("utf-8")
    return value


def ident(value):
    text(value, 1, 64)
    need(re.fullmatch(r"[a-z][a-z0-9_]{0,63}", value) is not None)
    return value


def seq(value, maximum=64, minimum=0):
    need(type(value) is list and minimum <= len(value) <= maximum)
    return value


def ids(value, maximum=64):
    seq(value, maximum)
    for item in value:
        ident(item)
    need(len(value) == len(set(value)))
    return value


def integer(value, low=0, high=1000000):
    need(type(value) in (int, float) and math.isfinite(value)
         and value == int(value) and low <= value <= high)
    return int(value)


def exact_integer_token(token):
    mantissa = re.split("[eE]", token, maxsplit=1)[0].lstrip("-").replace(".", "")
    if mantissa and not mantissa.strip("0"):
        return 0
    try:
        number = Decimal(token)
        need(number.is_finite() and number == number.to_integral_value()
             and number.copy_abs() <= 1000000000)
        return int(number)
    except InvalidOperation as error:
        raise ValueError("invalid number") from error


def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result)
        result[key] = value
    return result


def bounded(value, depth=0):
    need(depth <= 16)
    if type(value) is float:
        need(math.isfinite(value))
    elif type(value) is str:
        value.encode("utf-8")
    elif type(value) is dict:
        for key, item in value.items():
            key.encode("utf-8")
            bounded(item, depth + 1)
    elif type(value) is list:
        for item in value:
            bounded(item, depth + 1)


from fractions import Fraction

DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]{0,8}|1000000000)(?:\.[0-9]{1,6})?")


def measurement(value):
    if value is None:
        return None
    text(value, 1, 18)
    need(DECIMAL.fullmatch(value) is not None)
    number = Fraction(value)
    need(abs(number) <= 1000000000)
    return number


def solve(value):
    obj(value, ("direction", "pairs"))
    need(value["direction"] in ("higher", "lower"))
    seen = set()
    wins = losses = ties = missing = 0
    for pair in seq(value["pairs"], 128):
        obj(pair, ("id", "a", "b"))
        name = ident(pair["id"])
        need(name not in seen)
        seen.add(name)
        a, b = measurement(pair["a"]), measurement(pair["b"])
        if a is None or b is None:
            missing += 1
        elif a == b:
            ties += 1
        elif (b > a) == (value["direction"] == "higher"):
            wins += 1
        else:
            losses += 1
    trials = wins + losses
    probability = None
    if trials:
        probability = min(Fraction(1), Fraction(2 * sum(math.comb(trials, index)
                              for index in range(min(wins, losses) + 1)), 2 ** trials))
        probability = {"numerator": str(probability.numerator), "denominator": str(probability.denominator)}
    return {"wins": wins, "losses": losses, "ties": ties, "missing": missing,
            "evaluated": wins + losses + ties, "p_two_sided": probability}


def main():
    try:
        raw = sys.stdin.buffer.read(32769)
        need(len(raw) <= 32768)
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_float=exact_integer_token,
                           parse_constant=lambda _: need(False))
        bounded(value)
        result = solve(value)
        output = (json.dumps(result, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")
        need(len(output) <= 65536)
        sys.stdout.buffer.write(output)
        return 0
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, UnicodeError, RecursionError, ZeroDivisionError):
        sys.stdout.buffer.write(b'{"error":"invalid_input"}\n')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
