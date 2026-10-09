"""Shared numerics for the evaluation atoms: input validation, small dense linear algebra, distributions, seeded draws.

Standard library only (math, fractions, statistics, random). Matrices are lists of row lists of floats. Every routine
is written for small inputs (tens of rows) and for determinism: the same inputs give the same result on every
platform with IEEE 754 doubles, apart from last-bit differences in the platform's exp, log and trigonometric
functions. Validation raises ValueError naming the argument. No routine returns NaN or an infinity.

```text
numerics
├── validation      finite_number, integer, probability, vector, matrix, symmetric_matrix, labels, json_safe
├── linear algebra  identity, zeros, transpose, matmul, matvec, dot, outer, add, subtract, scale, trace, norms,
│                   solve, inverse, determinant, cholesky, symmetric_eigen, pseudo_inverse_symmetric,
│                   least_squares, matrix_power
├── statistics      mean, variance, covariance, covariance_matrix, average_ranks
├── distributions   normal_cdf, normal_survival, normal_pdf, normal_quantile, regularized_gamma_lower,
│                   regularized_gamma_upper, regularized_beta, beta_quantile, chi_square_survival,
│                   student_t_cdf, student_t_two_sided_p, f_survival, binomial_cdf
└── seeded draws    seeded_random, uniforms, standard_normals, random_index, shuffled, laplace_draws
```

Seeded draws use only ``random.Random.random()``, the one method whose sequence Python guarantees across versions
for an integer seed, so a seeded result does not change with the interpreter version.
"""
from __future__ import annotations

import json
import math
import random
import statistics
from fractions import Fraction

_NORMAL = statistics.NormalDist()
_TINY = 1e-300
#: Relative size below which a pivot or a diagonal entry counts as zero.
SINGULAR_TOLERANCE = 1e-12


# ----------------------------------------------------------------------------------------------- validation

def finite_number(value, name="value"):
    """``value`` as a finite float. Booleans, None, text and non-finite numbers raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float, Fraction)):
        raise ValueError(f"{name} must be a finite number, got {type(value).__name__}")
    try:
        result = float(value)
    except OverflowError:
        raise ValueError(f"{name} is too large for a float") from None
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def integer(value, name="value", minimum=None, maximum=None):
    """``value`` as an int. An integral float such as 3.0 is accepted; booleans and fractions are refused."""
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        value = int(value)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be at most {maximum}")
    return value


def probability(value, name="value", *, open_low=False, open_high=False):
    """A number in [0, 1]; ``open_low`` and ``open_high`` exclude 0 and 1."""
    result = finite_number(value, name)
    if result < 0.0 or result > 1.0 or (open_low and result == 0.0) or (open_high and result == 1.0):
        low, high = "(" if open_low else "[", ")" if open_high else "]"
        raise ValueError(f"{name} must lie in {low}0, 1{high}")
    return result


def vector(values, name="values", *, minimum_length=1, maximum_length=None):
    """A list of finite floats of the given length bounds."""
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{name} must be a list of numbers")
    result = [finite_number(value, f"{name}[{index}]") for index, value in enumerate(values)]
    if len(result) < minimum_length:
        raise ValueError(f"{name} needs at least {minimum_length} entries")
    if maximum_length is not None and len(result) > maximum_length:
        raise ValueError(f"{name} accepts at most {maximum_length} entries")
    return result


def matrix(rows, name="matrix", *, square=False, minimum_rows=1, minimum_columns=1, maximum_rows=None):
    """A rectangular list of rows of finite floats."""
    if not isinstance(rows, (list, tuple)):
        raise ValueError(f"{name} must be a list of rows")
    if len(rows) < minimum_rows:
        raise ValueError(f"{name} needs at least {minimum_rows} rows")
    if maximum_rows is not None and len(rows) > maximum_rows:
        raise ValueError(f"{name} accepts at most {maximum_rows} rows")
    result = [vector(row, f"{name}[{index}]", minimum_length=minimum_columns) for index, row in enumerate(rows)]
    if any(len(row) != len(result[0]) for row in result):
        raise ValueError(f"{name} must be rectangular")
    if square and len(result[0]) != len(result):
        raise ValueError(f"{name} must be square")
    return result


def symmetric_matrix(rows, name="matrix", tolerance=1e-9):
    """A square matrix that is symmetric to ``tolerance`` (relative to its largest entry), symmetrized exactly."""
    result = matrix(rows, name, square=True)
    size = len(result)
    largest = max(1.0, max(abs(value) for row in result for value in row))
    for i in range(size):
        for j in range(i + 1, size):
            if abs(result[i][j] - result[j][i]) > tolerance * largest:
                raise ValueError(f"{name} must be symmetric")
    return [[(result[i][j] + result[j][i]) / 2.0 for j in range(size)] for i in range(size)]


def labels(values, name="labels", *, minimum_length=1):
    """A list of text or integer labels (booleans refused)."""
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{name} must be a list")
    for index, value in enumerate(values):
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise ValueError(f"{name}[{index}] must be text or an integer")
    if len(values) < minimum_length:
        raise ValueError(f"{name} needs at least {minimum_length} entries")
    return list(values)


def json_safe(value):
    """``value`` after a strict JSON round trip: tuples become lists and a NaN or an infinity raises ValueError."""
    try:
        return json.loads(json.dumps(value, allow_nan=False, sort_keys=True))
    except (TypeError, ValueError) as error:
        raise ValueError(f"result is not finite JSON: {error}") from None


# ----------------------------------------------------------------------------------------------- linear algebra

def identity(size):
    """The ``size`` by ``size`` identity matrix."""
    return [[1.0 if i == j else 0.0 for j in range(size)] for i in range(size)]


def zeros(rows, columns):
    """A ``rows`` by ``columns`` matrix of zeros."""
    return [[0.0] * columns for _ in range(rows)]


def transpose(a):
    """The transpose of a rectangular matrix."""
    return [list(column) for column in zip(*a)]


def dot(x, y):
    """The inner product of two vectors of equal length, summed with math.fsum."""
    if len(x) != len(y):
        raise ValueError("vectors differ in length")
    return math.fsum(p * q for p, q in zip(x, y))


def matmul(a, b):
    """The matrix product a b."""
    if len(a[0]) != len(b):
        raise ValueError("inner dimensions differ")
    columns = transpose(b)
    return [[dot(row, column) for column in columns] for row in a]


def matvec(a, x):
    """The matrix-vector product a x."""
    if len(a[0]) != len(x):
        raise ValueError("inner dimensions differ")
    return [dot(row, x) for row in a]


def outer(x, y):
    """The outer product x y^T."""
    return [[p * q for q in y] for p in x]


def add(a, b):
    """The entrywise sum of two matrices of equal shape."""
    return [[p + q for p, q in zip(row_a, row_b)] for row_a, row_b in zip(a, b)]


def subtract(a, b):
    """The entrywise difference a - b of two matrices of equal shape."""
    return [[p - q for p, q in zip(row_a, row_b)] for row_a, row_b in zip(a, b)]


def scale(a, factor):
    """The matrix a multiplied by a scalar."""
    return [[factor * value for value in row] for row in a]


def trace(a):
    """The sum of the diagonal of a square matrix."""
    return math.fsum(a[i][i] for i in range(len(a)))


def frobenius_norm(a):
    """The square root of the sum of squared entries."""
    return math.sqrt(math.fsum(value * value for row in a for value in row))


def vector_norm(x):
    """The Euclidean norm of a vector."""
    return math.sqrt(math.fsum(value * value for value in x))


def _eliminate(a):
    """Gaussian elimination with partial pivoting on a copy of ``a``: (rows, swaps) or None when singular."""
    rows = [list(row) for row in a]
    size = len(rows)
    largest = max((abs(value) for row in a for value in row[:size]), default=0.0) or 1.0
    swaps = 0
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(rows[row][column]))
        if abs(rows[pivot][column]) <= SINGULAR_TOLERANCE * largest:
            return None, swaps
        if pivot != column:
            rows[column], rows[pivot] = rows[pivot], rows[column]
            swaps += 1
        for row in range(column + 1, size):
            factor = rows[row][column] / rows[column][column]
            if factor:
                rows[row] = [value - factor * lead for value, lead in zip(rows[row], rows[column])]
                rows[row][column] = 0.0
    return rows, swaps


def solve(a, b):
    """Solve a x = b for a square matrix ``a`` by Gaussian elimination with partial pivoting.

    ``b`` is a vector or a matrix of right-hand sides. A pivot at most 1e-12 times the largest entry of ``a`` counts
    as zero, and the matrix is then refused as singular with ValueError."""
    size = len(a)
    if size == 0 or any(len(row) != size for row in a):
        raise ValueError("solve needs a non-empty square matrix")
    if not b:
        raise ValueError("right-hand side is empty")
    single = not isinstance(b[0], (list, tuple))
    right = [[value] for value in b] if single else [list(row) for row in b]
    if len(right) != size:
        raise ValueError("right-hand side has the wrong number of rows")
    augmented = [list(row) + extra for row, extra in zip(a, right)]
    rows, _swaps = _eliminate(augmented)
    if rows is None:
        raise ValueError("matrix is singular to working precision")
    width = len(right[0])
    result = [[0.0] * width for _ in range(size)]
    for i in reversed(range(size)):
        for k in range(width):
            total = rows[i][size + k] - math.fsum(rows[i][j] * result[j][k] for j in range(i + 1, size))
            result[i][k] = total / rows[i][i]
    return [row[0] for row in result] if single else result


def inverse(a):
    """The inverse of a non-singular square matrix."""
    return solve(a, identity(len(a)))


def determinant(a):
    """The determinant of a square matrix (0.0 when it is singular to working precision)."""
    rows, swaps = _eliminate(a)
    if rows is None:
        return 0.0
    product = -1.0 if swaps % 2 else 1.0
    for i in range(len(rows)):
        product *= rows[i][i]
    return product


def cholesky(a, name="matrix"):
    """The lower-triangular L with a = L L^T; ValueError when ``a`` is not positive definite."""
    size = len(a)
    lower = zeros(size, size)
    largest = max(abs(a[i][i]) for i in range(size)) or 1.0
    for i in range(size):
        for j in range(i + 1):
            total = a[i][j] - math.fsum(lower[i][k] * lower[j][k] for k in range(j))
            if i == j:
                if total <= SINGULAR_TOLERANCE * largest:
                    raise ValueError(f"{name} is not positive definite")
                lower[i][i] = math.sqrt(total)
            else:
                lower[i][j] = total / lower[j][j]
    return lower


def symmetric_eigen(a, tolerance=1e-15, maximum_sweeps=100):
    """Eigenvalues (descending) and unit eigenvectors (the columns of the second result) of a symmetric matrix.

    Cyclic Jacobi rotations: each rotation zeroes one off-diagonal pair. Sweeps stop when the off-diagonal mass is at
    most ``tolerance`` squared times the total mass. Each eigenvector's largest-magnitude component is made
    positive, so the output is deterministic."""
    size = len(a)
    m = [list(map(float, row)) for row in a]
    vectors = identity(size)
    for _sweep in range(maximum_sweeps):
        off = math.fsum(m[i][j] * m[i][j] for i in range(size) for j in range(size) if i != j)
        total = math.fsum(m[i][j] * m[i][j] for i in range(size) for j in range(size))
        if off <= tolerance * tolerance * total or off == 0.0:
            break
        for p in range(size - 1):
            for q in range(p + 1, size):
                if m[p][q] == 0.0:
                    continue
                theta = (m[q][q] - m[p][p]) / (2.0 * m[p][q])
                t = (1.0 if theta >= 0 else -1.0) / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                apq = m[p][q]
                m[p][p] -= t * apq
                m[q][q] += t * apq
                m[p][q] = m[q][p] = 0.0
                for r in range(size):
                    if r != p and r != q:
                        arp, arq = m[r][p], m[r][q]
                        m[r][p] = m[p][r] = c * arp - s * arq
                        m[r][q] = m[q][r] = s * arp + c * arq
                for r in range(size):
                    vrp, vrq = vectors[r][p], vectors[r][q]
                    vectors[r][p] = c * vrp - s * vrq
                    vectors[r][q] = s * vrp + c * vrq
    else:
        raise ValueError("Jacobi rotations did not converge")
    order = sorted(range(size), key=lambda index: -m[index][index])
    values = [m[index][index] for index in order]
    columns = [[vectors[row][index] for row in range(size)] for index in order]
    for column in columns:
        lead = max(range(size), key=lambda row: abs(column[row]))
        if column[lead] < 0:
            column[:] = [-value for value in column]
    return values, transpose(columns)


def pseudo_inverse_symmetric(a, relative_cutoff=1e-10):
    """The Moore-Penrose inverse of a symmetric matrix; eigenvalues at most the cutoff times the largest are zero."""
    values, vectors = symmetric_eigen(a)
    size = len(a)
    largest = max((abs(value) for value in values), default=0.0)
    result = zeros(size, size)
    for index, value in enumerate(values):
        if largest == 0.0 or abs(value) <= relative_cutoff * largest:
            continue
        column = [vectors[row][index] for row in range(size)]
        for i in range(size):
            for j in range(size):
                result[i][j] += column[i] * column[j] / value
    return result


def least_squares(x, y, ridge=0.0):
    """Coefficients b minimizing ||x b - y||^2 + ridge ||b||^2, by Householder QR on the augmented system.

    ``x`` has full column rank when ``ridge`` is 0; a rank-deficient design raises ValueError."""
    ridge = finite_number(ridge, "ridge")
    if ridge < 0:
        raise ValueError("ridge must be non-negative")
    rows, columns = len(x), len(x[0])
    a = [list(row) for row in x]
    b = list(y)
    if len(b) != rows:
        raise ValueError("x and y differ in length")
    if ridge > 0:
        root = math.sqrt(ridge)
        for k in range(columns):
            a.append([root if j == k else 0.0 for j in range(columns)])
            b.append(0.0)
    total_rows = len(a)
    if total_rows < columns:
        raise ValueError("least squares needs at least as many rows as columns")
    for k in range(columns):
        column = [a[i][k] for i in range(k, total_rows)]
        length = vector_norm(column)
        if length == 0.0:
            continue
        alpha = -math.copysign(length, column[0])
        reflector = list(column)
        reflector[0] -= alpha
        size = vector_norm(reflector)
        if size == 0.0:
            continue
        reflector = [value / size for value in reflector]
        for j in range(k, columns):
            projection = 2.0 * math.fsum(reflector[i - k] * a[i][j] for i in range(k, total_rows))
            for i in range(k, total_rows):
                a[i][j] -= projection * reflector[i - k]
        projection = 2.0 * math.fsum(reflector[i - k] * b[i] for i in range(k, total_rows))
        for i in range(k, total_rows):
            b[i] -= projection * reflector[i - k]
    largest = max(abs(a[i][i]) for i in range(columns)) or 1.0
    if any(abs(a[i][i]) <= SINGULAR_TOLERANCE * largest for i in range(columns)):
        raise ValueError("design matrix is rank deficient")
    result = [0.0] * columns
    for i in reversed(range(columns)):
        result[i] = (b[i] - math.fsum(a[i][j] * result[j] for j in range(i + 1, columns))) / a[i][i]
    return result


def matrix_power(a, exponent):
    """a raised to a non-negative integer power by repeated squaring."""
    exponent = integer(exponent, "exponent", minimum=0)
    result, base = identity(len(a)), [list(row) for row in a]
    while exponent:
        if exponent & 1:
            result = matmul(result, base)
        exponent >>= 1
        if exponent:
            base = matmul(base, base)
    return result


# ----------------------------------------------------------------------------------------------- statistics

def mean(values):
    """The arithmetic mean, summed with math.fsum."""
    if not values:
        raise ValueError("mean of an empty list")
    return math.fsum(values) / len(values)


def variance(values, ddof=1):
    """The variance with ``ddof`` subtracted from the count (1 for the sample variance, 0 for the population)."""
    count = len(values)
    if count - ddof <= 0:
        raise ValueError(f"variance needs more than {ddof} values")
    centre = mean(values)
    return math.fsum((value - centre) ** 2 for value in values) / (count - ddof)


def covariance(x, y, ddof=1):
    """The covariance of two equal-length lists with ``ddof`` subtracted from the count."""
    if len(x) != len(y):
        raise ValueError("lists differ in length")
    count = len(x)
    if count - ddof <= 0:
        raise ValueError(f"covariance needs more than {ddof} values")
    mx, my = mean(x), mean(y)
    return math.fsum((p - mx) * (q - my) for p, q in zip(x, y)) / (count - ddof)


def covariance_matrix(rows, ddof=1):
    """The covariance matrix of the columns of ``rows`` (one observation per row)."""
    columns = transpose(rows)
    width = len(columns)
    return [[covariance(columns[i], columns[j], ddof) for j in range(width)] for i in range(width)]


def average_ranks(values):
    """Ranks from 1 (smallest) with tied values given the mean of the ranks they span."""
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        stop = start
        while stop + 1 < len(order) and values[order[stop + 1]] == values[order[start]]:
            stop += 1
        shared = (start + stop) / 2.0 + 1.0
        for position in range(start, stop + 1):
            ranks[order[position]] = shared
        start = stop + 1
    return ranks


# ----------------------------------------------------------------------------------------------- distributions

def normal_cdf(x):
    """The standard normal distribution function."""
    return _NORMAL.cdf(finite_number(x, "x"))


def normal_survival(x):
    """1 minus the standard normal distribution function, accurate in the upper tail."""
    return 0.5 * math.erfc(finite_number(x, "x") / math.sqrt(2.0))


def normal_pdf(x):
    """The standard normal density."""
    x = finite_number(x, "x")
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def normal_quantile(p):
    """The standard normal quantile for p in (0, 1)."""
    return _NORMAL.inv_cdf(probability(p, "p", open_low=True, open_high=True))


def _gamma_series(a, x):
    term = total = 1.0 / a
    denominator = a
    for _ in range(10000):
        denominator += 1.0
        term *= x / denominator
        total += term
        if abs(term) < abs(total) * 1e-16:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gamma_fraction(a, x):
    b = x + 1.0 - a
    c = 1.0 / _TINY
    d = 1.0 / b if b != 0 else 1.0 / _TINY
    result = d
    for i in range(1, 10000):
        coefficient = -i * (i - a)
        b += 2.0
        d = coefficient * d + b
        d = _TINY if abs(d) < _TINY else d
        c = b + coefficient / c
        c = _TINY if abs(c) < _TINY else c
        d = 1.0 / d
        step = d * c
        result *= step
        if abs(step - 1.0) < 1e-16:
            break
    return result * math.exp(-x + a * math.log(x) - math.lgamma(a))


def regularized_gamma_lower(a, x):
    """P(a, x), the regularized lower incomplete gamma function (series below a + 1, continued fraction above)."""
    a, x = finite_number(a, "a"), finite_number(x, "x")
    if a <= 0 or x < 0:
        raise ValueError("regularized gamma needs a > 0 and x >= 0")
    if x == 0:
        return 0.0
    return _gamma_series(a, x) if x < a + 1.0 else 1.0 - _gamma_fraction(a, x)


def regularized_gamma_upper(a, x):
    """Q(a, x) = 1 - P(a, x), computed directly in the upper tail."""
    a, x = finite_number(a, "a"), finite_number(x, "x")
    if a <= 0 or x < 0:
        raise ValueError("regularized gamma needs a > 0 and x >= 0")
    if x == 0:
        return 1.0
    return 1.0 - _gamma_series(a, x) if x < a + 1.0 else _gamma_fraction(a, x)


def _beta_fraction(x, a, b):
    c, d = 1.0, 1.0 - (a + b) * x / (a + 1.0)
    d = 1.0 / (_TINY if abs(d) < _TINY else d)
    result = d
    for m in range(1, 10000):
        even = m * (b - m) * x / ((a + 2 * m - 1.0) * (a + 2 * m))
        d = 1.0 + even * d
        d = 1.0 / (_TINY if abs(d) < _TINY else d)
        c = 1.0 + even / c
        c = _TINY if abs(c) < _TINY else c
        result *= d * c
        odd = -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1.0))
        d = 1.0 + odd * d
        d = 1.0 / (_TINY if abs(d) < _TINY else d)
        c = 1.0 + odd / c
        c = _TINY if abs(c) < _TINY else c
        step = d * c
        result *= step
        if abs(step - 1.0) < 1e-16:
            break
    return result


def regularized_beta(x, a, b):
    """I_x(a, b), the regularized incomplete beta function, by its continued fraction and the symmetry
    I_x(a, b) = 1 - I_(1-x)(b, a)."""
    x, a, b = finite_number(x, "x"), finite_number(a, "a"), finite_number(b, "b")
    if a <= 0 or b <= 0:
        raise ValueError("regularized beta needs a > 0 and b > 0")
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_front = (a * math.log(x) + b * math.log1p(-x) + math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b))
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(log_front) * _beta_fraction(x, a, b) / a
    return 1.0 - math.exp(log_front) * _beta_fraction(1.0 - x, b, a) / b


def beta_quantile(p, a, b):
    """The x with I_x(a, b) = p, by bisection to 1e-15."""
    p = probability(p, "p")
    if p == 0.0:
        return 0.0
    if p == 1.0:
        return 1.0
    low, high = 0.0, 1.0
    for _ in range(200):
        middle = (low + high) / 2.0
        if regularized_beta(middle, a, b) < p:
            low = middle
        else:
            high = middle
        if high - low < 1e-15:
            break
    return (low + high) / 2.0


def chi_square_survival(x, degrees_of_freedom):
    """P(X > x) for a chi-square variable with the given degrees of freedom."""
    x = finite_number(x, "x")
    degrees_of_freedom = finite_number(degrees_of_freedom, "degrees_of_freedom")
    if degrees_of_freedom <= 0:
        raise ValueError("degrees_of_freedom must be positive")
    return 1.0 if x <= 0 else regularized_gamma_upper(degrees_of_freedom / 2.0, x / 2.0)


def student_t_two_sided_p(t, degrees_of_freedom):
    """P(|T| >= |t|) for Student's t with the given degrees of freedom."""
    t = finite_number(t, "t")
    nu = finite_number(degrees_of_freedom, "degrees_of_freedom")
    if nu <= 0:
        raise ValueError("degrees_of_freedom must be positive")
    return regularized_beta(nu / (nu + t * t), nu / 2.0, 0.5)


def student_t_cdf(t, degrees_of_freedom):
    """P(T <= t) for Student's t with the given degrees of freedom."""
    tail = student_t_two_sided_p(t, degrees_of_freedom) / 2.0
    return 1.0 - tail if t > 0 else tail


def f_survival(f, numerator_df, denominator_df):
    """P(F > f) for Snedecor's F with the given degrees of freedom."""
    f = finite_number(f, "f")
    d1, d2 = finite_number(numerator_df, "numerator_df"), finite_number(denominator_df, "denominator_df")
    if d1 <= 0 or d2 <= 0:
        raise ValueError("degrees of freedom must be positive")
    return 1.0 if f <= 0 else regularized_beta(d2 / (d2 + d1 * f), d2 / 2.0, d1 / 2.0)


def binomial_cdf(k, n, p):
    """P(X <= k) for X binomial with n trials and success probability p, through I_(1-p)(n - k, k + 1)."""
    n = integer(n, "n", minimum=0)
    k = integer(k, "k")
    p = probability(p, "p")
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    if p == 0.0:
        return 1.0
    if p == 1.0:
        return 0.0
    return regularized_beta(1.0 - p, n - k, k + 1)


# ----------------------------------------------------------------------------------------------- seeded draws

def seeded_random(seed):
    """A random.Random seeded with a non-negative integer."""
    return random.Random(integer(seed, "seed", minimum=0))


def uniforms(generator, count):
    """``count`` draws from [0, 1) using random() alone."""
    return [generator.random() for _ in range(integer(count, "count", minimum=0))]


def standard_normals(generator, count):
    """``count`` standard normal draws by the Box-Muller transform of random() pairs."""
    count = integer(count, "count", minimum=0)
    draws = []
    while len(draws) < count:
        first, second = generator.random(), generator.random()
        if first <= 0.0:
            continue
        radius = math.sqrt(-2.0 * math.log(first))
        draws.append(radius * math.cos(2.0 * math.pi * second))
        draws.append(radius * math.sin(2.0 * math.pi * second))
    return draws[:count]


def random_index(generator, size):
    """An index in range(size) from one random() draw."""
    size = integer(size, "size", minimum=1)
    return min(int(generator.random() * size), size - 1)


def shuffled(generator, items):
    """A Fisher-Yates shuffle of a copy of ``items`` driven by random() alone."""
    result = list(items)
    for position in range(len(result) - 1, 0, -1):
        other = random_index(generator, position + 1)
        result[position], result[other] = result[other], result[position]
    return result


def laplace_draws(generator, count, scale_parameter):
    """``count`` draws from a centred Laplace distribution with the given scale, by inverting its distribution."""
    scale_parameter = finite_number(scale_parameter, "scale_parameter")
    if scale_parameter < 0:
        raise ValueError("scale_parameter must be non-negative")
    draws = []
    for _ in range(integer(count, "count", minimum=0)):
        u = generator.random() - 0.5
        draws.append(0.0 if scale_parameter == 0 else
                     -scale_parameter * math.copysign(1.0, u) * math.log(max(1.0 - 2.0 * abs(u), _TINY)))
    return draws


__all__ = ["SINGULAR_TOLERANCE", "finite_number", "integer", "probability", "vector", "matrix", "symmetric_matrix",
           "labels", "json_safe", "identity", "zeros", "transpose", "dot", "matmul", "matvec", "outer", "add",
           "subtract", "scale", "trace", "frobenius_norm", "vector_norm", "solve", "inverse", "determinant",
           "cholesky", "symmetric_eigen", "pseudo_inverse_symmetric", "least_squares", "matrix_power", "mean",
           "variance", "covariance", "covariance_matrix", "average_ranks", "normal_cdf", "normal_survival",
           "normal_pdf", "normal_quantile", "regularized_gamma_lower", "regularized_gamma_upper",
           "regularized_beta", "beta_quantile", "chi_square_survival", "student_t_two_sided_p", "student_t_cdf",
           "f_survival", "binomial_cdf", "seeded_random", "uniforms", "standard_normals", "random_index",
           "shuffled", "laplace_draws"]
