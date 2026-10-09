"""Original, renderer-independent numeric operations for creative components.

These are pure implementation helpers invoked through an owning Loop. They
do not introduce a runtime or perform file, model, network or rendering work.
Angles are radians and elapsed times are seconds unless stated otherwise.
"""
from __future__ import annotations

import math


def _finite(*values):
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in values):
        raise ValueError("finite numbers required")


def _positive(*values):
    _finite(*values)
    if any(value <= 0 for value in values):
        raise ValueError("positive numbers required")


def _unit(value):
    _finite(value)
    if not 0 <= value <= 1:
        raise ValueError("value must lie in [0, 1]")


def smoothstep(t):
    """Cubic transition on [0, 1], with zero slope at both ends."""
    _unit(t)
    return t * t * (3 - 2 * t)


def smootherstep(t):
    """Quintic transition with zero first and second endpoint derivatives."""
    _unit(t)
    return t ** 3 * (t * (6 * t - 15) + 10)


def quadratic_in(t):
    """Accelerating quadratic progress on [0, 1]."""
    _unit(t)
    return t * t


def quadratic_out(t):
    """Decelerating quadratic progress on [0, 1]."""
    _unit(t)
    return t * (2 - t)


def cubic_in(t):
    """Accelerating cubic progress on [0, 1]."""
    _unit(t)
    return t ** 3


def cubic_out(t):
    """Decelerating cubic progress on [0, 1]."""
    _unit(t)
    return 1 - (1 - t) ** 3


def sine_in_out(t):
    """Cosine-based progress with smooth entry and exit."""
    _unit(t)
    return (1 - math.cos(math.pi * t)) / 2


def ping_pong(phase):
    """Periodic triangular progress; integer phases start a new cycle."""
    _finite(phase)
    return 1 - abs(2 * (phase % 1) - 1)


def linear_mix(a, b, t):
    """Interpolate two scalars without extrapolation."""
    _finite(a, b)
    _unit(t)
    return (1 - t) * a + t * b


def quadratic_bezier(a, b, c, t):
    """Evaluate one coordinate of a quadratic Bezier curve."""
    _finite(a, b, c)
    _unit(t)
    return (1 - t) ** 2 * a + 2 * (1 - t) * t * b + t * t * c


def cubic_bezier(a, b, c, d, t):
    """Evaluate one coordinate of a cubic Bezier curve."""
    _finite(a, b, c, d)
    _unit(t)
    return (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * c + t ** 3 * d


def frame_time(frame, rate):
    """Map a nonnegative integer frame index to seconds at a positive rate."""
    _positive(rate)
    if type(frame) is not int or frame < 0:
        raise ValueError("frame must be a nonnegative integer")
    return frame / rate


def frame_progress(frame, frame_count):
    """Map a discrete frame to [0, 1], including both endpoints; a one-frame shot returns zero."""
    if type(frame) is not int or type(frame_count) is not int or frame_count < 1 or not 0 <= frame < frame_count:
        raise ValueError("frame and frame count must be valid integers")
    return frame / (frame_count - 1) if frame_count > 1 else 0


def beat_time(beat, bpm):
    """Map a nonnegative beat position to seconds at constant tempo."""
    _finite(beat)
    _positive(bpm)
    if beat < 0:
        raise ValueError("beat must be nonnegative")
    return beat * 60 / bpm


def segment_progress(time, start, duration):
    """Clamp absolute time to the normalized progress of one segment."""
    _finite(time, start)
    _positive(duration)
    return min(1, max(0, (time - start) / duration))


def fit_inside(width, height, frame_width, frame_height):
    """Return centered [x, y, width, height] without cropping or distortion."""
    _positive(width, height, frame_width, frame_height)
    scale = min(frame_width / width, frame_height / height)
    w, h = width * scale, height * scale
    return [(frame_width - w) / 2, (frame_height - h) / 2, w, h]


def cover_frame(width, height, frame_width, frame_height):
    """Return centered [x, y, width, height] covering a frame; crop is explicit."""
    _positive(width, height, frame_width, frame_height)
    scale = max(frame_width / width, frame_height / height)
    w, h = width * scale, height * scale
    return [(frame_width - w) / 2, (frame_height - h) / 2, w, h]


def _bounded_product_ratio(value, numerator, denominator, bound):
    """Return min(bound, value * numerator / denominator) without an overflowing intermediate."""
    value_mantissa, value_exponent = math.frexp(value)
    numerator_mantissa, numerator_exponent = math.frexp(numerator)
    denominator_mantissa, denominator_exponent = math.frexp(denominator)
    try:
        result = math.ldexp(value_mantissa * (numerator_mantissa / denominator_mantissa),
                            value_exponent + numerator_exponent - denominator_exponent)
    except OverflowError:
        return bound
    return min(bound, result)


def focal_crop(width, height, frame_width, frame_height, zoom, focus_x, focus_y):
    """Return in-image [x, y, width, height]; normalized focus, zoom >= 1, y down; refuse aspect error above 1e-12 relative."""
    _positive(width, height, frame_width, frame_height, zoom)
    _unit(focus_x)
    _unit(focus_y)
    if zoom < 1:
        raise ValueError("zoom must be at least one")
    w = _bounded_product_ratio(height, frame_width, frame_height, width) / zoom
    h = _bounded_product_ratio(width, frame_height, frame_width, height) / zoom
    _positive(w, h)
    wm, we = math.frexp(w)
    hm, he = math.frexp(h)
    fm, fe = math.frexp(frame_width)
    gm, ge = math.frexp(frame_height)
    aspect_ratio = math.ldexp((wm / hm) * (gm / fm), we - he + ge - fe)
    if not math.isclose(aspect_ratio, 1, rel_tol=1e-12, abs_tol=0):
        raise ValueError("crop aspect cannot be represented")
    return [max(0, min(width - w, focus_x * width - w / 2)),
            max(0, min(height - h, focus_y * height - h / 2)), w, h]


def subject_safe_axis(image_extent, crop_extent, subject_start, subject_end, focus):
    """Return [origin, minimum, maximum] for a whole positive-length subject interval; focus lies in [0, 1]."""
    _positive(image_extent, crop_extent)
    _finite(subject_start, subject_end)
    _unit(focus)
    if crop_extent > image_extent or not 0 <= subject_start < subject_end <= image_extent:
        raise ValueError("crop and subject must be inside the image axis")
    if subject_end - subject_start > crop_extent:
        raise ValueError("subject cannot fit inside this crop")
    lower = max(0, subject_end - crop_extent)
    upper = min(subject_start, image_extent - crop_extent)
    if lower > upper:
        raise ValueError("subject cannot fit inside this crop")
    return [max(lower, min(upper, focus * image_extent - crop_extent / 2)), lower, upper]


def rotate_point(x, y, angle):
    """Rotate [x, y] counterclockwise in a Cartesian y-up plane."""
    _finite(x, y, angle)
    c, s = math.cos(angle), math.sin(angle)
    return [c * x - s * y, s * x + c * y]


def orbit_point(radius, angle, height):
    """Return [x, y, z] on a circle in the x-z plane of a y-up frame."""
    _positive(radius)
    _finite(angle, height)
    return [radius * math.cos(angle), height, radius * math.sin(angle)]


def circle_distance(x, y, radius):
    """Signed distance to an origin-centered circle; negative is inside."""
    _finite(x, y)
    _positive(radius)
    return math.hypot(x, y) - radius


def sphere_distance(x, y, z, radius):
    """Signed distance to an origin-centered sphere; negative is inside."""
    _finite(x, y, z)
    _positive(radius)
    return math.hypot(x, y, z) - radius


def normalize_three(x, y, z):
    """Return a unit vector; reject the undefined zero direction."""
    _finite(x, y, z)
    scale = max(abs(x), abs(y), abs(z))
    if scale == 0:
        raise ValueError("zero vector has no direction")
    scaled = [x / scale, y / scale, z / scale]
    length = math.hypot(*scaled)
    return [value / length for value in scaled]


def cross_three(ax, ay, az, bx, by, bz):
    """Right-handed cross product of two three-dimensional vectors."""
    _finite(ax, ay, az, bx, by, bz)
    return [ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx]


def wrap_angle(angle):
    """Normalize an angle into [-pi, pi), mapping pi to -pi."""
    _finite(angle)
    return (angle + math.pi) % (2 * math.pi) - math.pi


def jump_velocity(height, gravity):
    """Upward launch speed for target apex height under constant gravity magnitude."""
    _positive(height, gravity)
    return math.sqrt(2 * gravity * height)


def ballistic_height(velocity, gravity, time):
    """Y-up displacement with constant downward gravity and no drag or collision."""
    _finite(velocity, time)
    _positive(gravity)
    if time < 0:
        raise ValueError("elapsed time must be nonnegative")
    return velocity * time - gravity * time * time / 2


def linear_drag(velocity, drag, time):
    """Exact scalar velocity decay for dv/dt=-drag*v, with no external force."""
    _finite(velocity, drag, time)
    if drag < 0 or time < 0:
        raise ValueError("drag and elapsed time must be nonnegative")
    return velocity * math.exp(-drag * time)


def critical_step(time, omega):
    """Unit step of a critically damped second-order system at rest."""
    _finite(time)
    _positive(omega)
    if time < 0:
        raise ValueError("elapsed time must be nonnegative")
    return 1 - (1 + omega * time) * math.exp(-omega * time)


def midi_frequency(note):
    """Equal-tempered frequency in hertz, with MIDI 69 fixed at 440 hertz."""
    _finite(note)
    if not 0 <= note <= 127:
        raise ValueError("MIDI note must lie in [0, 127]")
    return 440 * 2 ** ((note - 69) / 12)


def amplitude_to_db(amplitude):
    """Amplitude decibels relative to one; zero has no finite logarithm."""
    _positive(amplitude)
    return 20 * math.log10(amplitude)


def db_to_amplitude(db):
    """Convert bounded amplitude decibels to a linear multiplier."""
    _finite(db)
    if not -600 <= db <= 600:
        raise ValueError("decibels must lie in [-600, 600]")
    return 10 ** (db / 20)


def equal_power_pan(pan):
    """Return stereo gains for pan in [-1, 1]; squared gains sum to one."""
    _finite(pan)
    if not -1 <= pan <= 1:
        raise ValueError("pan must lie in [-1, 1]")
    angle = (pan + 1) * math.pi / 4
    return [math.cos(angle), math.sin(angle)]


def alpha_over(foreground, background):
    """Composite alpha coverage only; this does not composite color channels."""
    _unit(foreground)
    _unit(background)
    return foreground + background * (1 - foreground)


def srgb_to_linear(channel):
    """Decode one normalized sRGB channel, not a complete color profile transform."""
    _unit(channel)
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def linear_to_srgb(channel):
    """Encode one normalized linear-light channel as sRGB."""
    _unit(channel)
    return 12.92 * channel if channel <= 0.0031308 else 1.055 * channel ** (1 / 2.4) - 0.055


def contrast_ratio(light, dark):
    """Contrast ratio from two relative luminances, accepting either order."""
    _unit(light)
    _unit(dark)
    return (max(light, dark) + 0.05) / (min(light, dark) + 0.05)
