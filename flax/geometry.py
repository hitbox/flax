from collections import deque
from enum import Enum


class classproperty(object):
    def __init__(self, f):
        self.f = f

    def __get__(self, obj, owner):
        return self.f(owner)


class Direction(Enum):
    up = (0, -1)
    up_right = (1, -1)
    right = (1, 0)
    down_right = (1, 1)
    down = (0, 1)
    down_left = (-1, 1)
    left = (-1, 0)
    up_left = (-1, -1)

    @classproperty
    def orthogonal(cls):
        return frozenset((cls.up, cls.down, cls.left, cls.right))

    @classproperty
    def diagonal(cls):
        return frozenset((cls.up_left, cls.up_right, cls.down_left, cls.down_right))

    def adjacent_to(self, other):
        return (
            (self.value[0] == other.value[0] and
                abs(self.value[1] - other.value[1]) <= 1) or
            (self.value[1] == other.value[1] and
                abs(self.value[0] - other.value[0]) <= 1)
        )

    @property
    def opposite(self):
        return Direction((- self.value[0], - self.value[1]))




class Point(tuple):
    def __new__(cls, x, y):
        return tuple.__new__(cls, (x, y))

    @classmethod
    def origin(cls):
        return cls(0, 0)

    @property
    def x(self):
        return self[0]

    @property
    def y(self):
        return self[1]

    @property
    def neighbors(self):
        return [self + d for d in Direction]

    def __add__(self, other):
        if isinstance(other, Direction):
            other = other.value
        elif isinstance(other, (Point, Size)):
            pass
        else:
            return NotImplemented

        return Point(self.x + other[0], self.y + other[1])

    def __sub__(self, other):
        if isinstance(other, Direction):
            other = other.value
        elif isinstance(other, (Point, Size)):
            pass
        else:
            return NotImplemented

        return Point(self.x - other[0], self.y - other[1])


class Size(tuple):
    def __new__(cls, width, height):
        assert width >= 0
        assert height >= 0
        return super().__new__(cls, (width, height))

    def __floordiv__(self, n):
        if not isinstance(n, (int, float)):
            return NotImplemented
        assert n > 0

        return type(self)(self[0] // n, self[1] // n)

    @property
    def width(self):
        return self[0]

    @property
    def height(self):
        return self[1]

    @property
    def area(self):
        return self.width * self.height

    def to_rect(self, point):
        return Rectangle(point, self)


class Span(tuple):
    """A one-dimensional range, with inclusive endpoints."""
    def __new__(cls, start, end):
        return super().__new__(cls, (start, end))

    @property
    def start(self):
        return self[0]

    @property
    def end(self):
        return self[1]

    def __contains__(self, point):
        return self.start <= point <= self.end

    def __iter__(self):
        return iter(range(self.start, self.end + 1))

    def __len__(self):
        return self.end - self.start + 1

    def __add__(self, n):
        cls = type(self)
        if isinstance(n, int):
            return cls(self.start + n, self.end + n)

        return NotImplemented

    def __sub__(self, n):
        return self + -n

    def overlaps(self, other):
        """Return whether `self` and `other` have any points in common."""
        return self.start <= other.end and self.end >= other.start

    def shift_into_view(self, point, *, margin=0):
        """Return a new `Span` that contains the given `point`, moving the
        endpoints as little as possible.

        That is, if this span currently does NOT contain the given `point`, the
        returned `Span` will have `point` as one of its endpoints.

        If `margin` is provided, the `point` must end up at least `margin` away
        from the endpoints.
        """
        if self.start + margin <= point <= self.end - margin:
            return self

        assert isinstance(point, int)
        assert isinstance(margin, int)
        assert margin > 0

        # Move left if the point is further left than the start, or right if
        # the point is further right than the end.
        d = (
            min(0, point - (self.start + margin)) +
            max(0, point - (self.end - margin))
        )

        return self + d

    def scale(self, width, *, pivot=None):
        old_width = len(self)

        if old_width == width:
            return self

        if pivot is None:
            pivot = (self.start + self.end) // 2

        cls = type(self)

        relative_pos = (pivot - self.start) / old_width

        start_offset = relative_pos * width
        # Round such that the nearer edge gets more space
        if relative_pos <= 0.5:
            start_offset = int(start_offset + 0.5)
        else:
            start_offset = int(start_offset)

        start = pivot - start_offset
        end = start + width - 1
        return cls(start, end)


class Rectangle(tuple):
    """A rectangle.  Note that since we're working with tiles instead of
    coordinates, the edges here are inclusive on all sides; half the point of
    this class is to take care of all the +1/-1 that requires.

    The origin is assumed to be the top left.
    """
    def __new__(cls, origin, size):
        return super().__new__(cls, (origin, size))

    @classmethod
    def from_edges(cls, *, top, bottom, left, right):
        return cls(Point(left, top), Size(right - left + 1, bottom - top + 1))

    @classmethod
    def from_spans(cls, *, vertical, horizontal):
        return cls.from_edges(
            top=vertical.start, bottom=vertical.end,
            left=horizontal.start, right=horizontal.end,
        )

    @classmethod
    def centered_at(cls, size, center):
        left = center.x - size.width // 2
        top = center.y - size.height // 2
        return cls(Point(left, top), size)

    @property
    def topleft(self):
        return self[0]

    @property
    def size(self):
        return self[1]

    @property
    def top(self):
        return self.topleft.y

    @property
    def bottom(self):
        return self.topleft.y + self.size.height - 1

    @property
    def left(self):
        return self.topleft.x

    @property
    def right(self):
        return self.topleft.x + self.size.width - 1

    @property
    def width(self):
        return self.size.width

    @property
    def height(self):
        return self.size.height

    @property
    def area(self):
        return self.size.area

    @property
    def vertical_span(self):
        return Span(self.top, self.bottom)

    @property
    def horizontal_span(self):
        return Span(self.left, self.right)

    def edge_length(self, edge):
        if edge is Direction.up or edge is Direction.down:
            return self.width
        if edge is Direction.left or edge is Direction.right:
            return self.height
        raise ValueError("Expected an orthogonal direction")

    def edge_span(self, edge):
        if edge is Direction.up or edge is Direction.down:
            return self.horizontal_span
        if edge is Direction.left or edge is Direction.right:
            return self.vertical_span
        raise ValueError("Expected an orthogonal direction")

    def edge_point(self, edge, parallel, orthogonal):
        """Return a point, relative to a particular edge.

        `parallel` is the absolute coordinate parallel to the given edge.  For
        example, if `edge` is `Direction.top`, then `parallel` is the
        x-coordinate.

        `orthogonal` is the RELATIVE offset from the given edge, towards the
        interior of the rectangle.  So for `Direction.top`, the y-coordinate is
        ``self.top + orthogonal``.
        """
        if edge is Direction.up:
            return Point(parallel, self.top + orthogonal)
        elif edge is Direction.down:
            return Point(parallel, self.bottom - orthogonal)
        elif edge is Direction.left:
            return Point(self.left + orthogonal, parallel)
        elif edge is Direction.right:
            return Point(self.right - orthogonal, parallel)
        raise ValueError("Expected an orthogonal direction")

    def relative_point(self, relative_width, relative_height):
        """Find a point x% across the width and y% across the height.  The
        arguments should be floats between 0 and 1.

        For example, ``relative_point(0, 0)`` returns the top left, and
        ``relative_point(0.5, 0.5)`` returns the center.
        """
        return Point(
            self.left + int((self.width - 1) * relative_width + 0.5),
            self.top + int((self.height - 1) * relative_height + 0.5),
        )

    def center(self):
        return self.relative_point(0.5, 0.5)

    def __contains__(self, other):
        if isinstance(other, Rectangle):
            return (
                self.top <= other.top and
                self.bottom >= other.bottom and
                self.left <= other.left and
                self.right >= other.right
            )
        elif isinstance(other, Point):
            return (
                self.left <= other.x <= self.right and
                self.top <= other.y <= self.bottom
            )
        else:
            return False

    def replace(self, *, top=None, bottom=None, left=None, right=None):
        if top is None:
            top = self.top
        if bottom is None:
            bottom = self.bottom
        if left is None:
            left = self.left
        if right is None:
            right = self.right

        return type(self).from_edges(
            top=top,
            bottom=bottom,
            left=left,
            right=right,
        )

    def shift(self, *, top=0, bottom=0, left=0, right=0):
        return type(self).from_edges(
            top=self.top + top,
            bottom=self.bottom + bottom,
            left=self.left + left,
            right=self.right + right,
        )

    def shrink(self, amount):
        new_left = self.left + amount
        new_right = self.right - amount
        if new_left > new_right:
            new_left = new_right = (self.left + self.right) // 2

        new_top = self.top + amount
        new_bottom = self.bottom - amount
        if new_top > new_bottom:
            new_top = new_bottom = (self.top + self.bottom) // 2

        return type(self).from_edges(
            top=new_top, bottom=new_bottom,
            left=new_left, right=new_right,
        )

    def iter_border(self):
        for x in range(self.left + 1, self.right):
            yield Point(x, self.top), Direction.up
            yield Point(x, self.bottom), Direction.down

        for y in range(self.top + 1, self.bottom):
            yield Point(self.left, y), Direction.left
            yield Point(self.right, y), Direction.right

        yield Point(self.left, self.top), Direction.up_left
        yield Point(self.right, self.top), Direction.up_right
        yield Point(self.left, self.bottom), Direction.down_left
        yield Point(self.right, self.bottom), Direction.down_right

    def iter_points(self):
        """Iterate over all tiles within this rectangle as points."""
        for x in range(self.left, self.right + 1):
            for y in range(self.top, self.bottom + 1):
                yield Point(x, y)

    def range_width(self):
        """Iterate over every x-coordinate within the width of the rectangle.
        """
        return range(self.left, self.right + 1)

    def range_height(self):
        """Iterate over every y-coordinate within the height of the rectangle.
        """
        return range(self.top, self.bottom + 1)


class Blob:
    """A region of arbitrary shape, containing an arbitrary set of discrete
    points.

    Intended for (and will perform best with) regions that are mostly
    contiguous.
    """
    def __init__(self, spans):
        # Mapping of y => ordered tuple of non-overlapping spans
        self.spans = spans

    @classmethod
    def from_rectangle(cls, rect):
        value = (rect.horizontal_span,)
        spans = dict.fromkeys(rect.range_height(), value)
        return cls(spans)

    def __contains__(self, point):
        if not isinstance(point, Point):
            return NotImplemented

        x = point.x
        for span in self.spans.get(point.y, ()):
            if x in span:
                return True

        return False

    @property
    def height(self):
        if not self.spans:
            return 0
        return max(self.spans) - min(self.spans) + 1

    @property
    def area(self):
        return sum(
            len(span)
            for spans in self.spans.values()
            for span in spans
        )

    def __eq__(self, other):
        if not isinstance(other, Blob):
            return NotImplemented

        return self.spans == other.spans

    def __add__(self, other):
        if not isinstance(other, Blob):
            return NotImplemented

        new_spans = {}
        for y in self.spans.keys() | other.spans.keys():
            if y not in self.spans:
                new_spans[y] = other.spans[y]
            elif y not in other.spans:
                new_spans[y] = self.spans[y]
            else:
                my_spans = deque(self.spans[y])
                combined_spans = []

                # For each 'other' span, find which spans it overlaps, and
                # merge all of them into a single new span.
                for span in other.spans[y]:
                    starts = [span.start]
                    ends = [span.end]
                    while my_spans and span.overlaps(my_spans[0]):
                        subsumed_span = my_spans.popleft()
                        starts.append(subsumed_span.start)
                        ends.append(subsumed_span.end)

                    combined_spans.append(Span(min(starts), max(ends)))

                combined_spans.extend(my_spans)
                combined_spans.sort()

                new_spans[y] = tuple(combined_spans)

        return type(self)(new_spans)

    def __sub__(self, other):
        if not isinstance(other, Blob):
            return NotImplemented

        new_spans = {}
        for y, spans in self.spans.items():
            if y not in other.spans:
                # Nothing to remove
                new_spans[y] = spans
                continue

            other_spans = deque(other.spans[y])
            resolved_spans = []
            for span in spans:
                # Remove any subtracted spans that don't overlap ours
                while other_spans and other_spans[0].end < span.start:
                    other_spans.popleft()

                for other_span in other_spans:
                    if not span.overlaps(other_span):
                        break

                    # Subtracting one span from another may leave zero, one, or
                    # two pieces remaining: the left end, the right end, both,
                    # or neither.  Check for each end.
                    # Note that we need a < on the matching end, because if the
                    # subtracted span has the same endpoint, there's nothing
                    # left over on that end to make a new span.
                    if span.start < other_span.start <= span.end:
                        left_piece = Span(span.start, other_span.start - 1)
                        resolved_spans.append(left_piece)

                    if span.start <= other_span.end < span.end:
                        right_piece = Span(other_span.end + 1, span.end)
                        # DON'T add the right piece yet -- it might intersect
                        # another subtracted span!  Instead, treat it as the
                        # current span.
                        span = right_piece
                    else:
                        # There was a left overlap, but no right overlap, so
                        # there's nothing left to subtract from.
                        span = None
                        break

                # Add any leftover span
                if span:
                    resolved_spans.append(span)

            if resolved_spans:
                new_spans[y] = tuple(resolved_spans)

        return type(self)(new_spans)

    def iter_points(self):
        for y, spans in self.spans.items():
            for span in spans:
                for x in span:
                    yield Point(x, y)
