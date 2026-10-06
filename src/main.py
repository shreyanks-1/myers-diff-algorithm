import sys
from array import array


def read_lines(path):
    # read raw bytes, split on \n, a final \n does not make an extra line
    with open(path, "rb") as f:
        data = f.read()
    lines = data.split(b"\n")
    if lines[-1] == b"":
        lines.pop()
    return lines


def myers(a, b):
    # Returns the edit script as a list of '=', '-', '+'
    # '=' keep, '-' delete from a, '+' insert from b

    # lines that are the same at the start and at the end are always kept,
    # so cut them off first. This makes big files with few changes fast.
    n = len(a)
    m = len(b)
    start = 0
    while start < n and start < m and a[start] == b[start]:
        start += 1
    end = 0
    while end < n - start and end < m - start and a[n - 1 - end] == b[m - 1 - end]:
        end += 1

    middle = shortest_edit(a[start:n - end], b[start:m - end])
    return ['='] * start + middle + ['='] * end


def shortest_edit(a, b):
    n = len(a)
    m = len(b)
    max_d = n + m
    offset = max_d + 1          # so that v[offset + k] works for negative k
    # v[offset + k] = furthest x on diagonal k
    # array of ints instead of a list, it uses much less memory
    v = array('i', [0]) * (2 * max_d + 3)
    trace = []                  # trace[d] = v values for k = -d..d after step d

    for d in range(max_d + 1):
        for k in range(-d, d + 1, 2):
            i = offset + k
            # go down (insert) from diagonal k+1, or right (delete) from k-1
            if k == -d or (k != d and v[i - 1] < v[i + 1]):
                x = v[i + 1]
            else:
                x = v[i - 1] + 1
            y = x - k

            # snake: follow equal lines for free
            while x < n and y < m and a[x] == b[y]:
                x += 1
                y += 1

            v[i] = x

            if x >= n and y >= m:
                trace.append(v[offset - d:offset + d + 1])
                return backtrack(trace, n, m)

        # save only the part we used in this step, not the whole array
        trace.append(v[offset - d:offset + d + 1])

    return []


def backtrack(trace, n, m):
    # walk from (n, m) back to (0, 0) and collect the moves in reverse
    ops = []
    x = n
    y = m
    for d in range(len(trace) - 1, 0, -1):
        prev = trace[d - 1]     # prev[k + d - 1] is the value for diagonal k
        k = x - y

        if k == -d or (k != d and prev[k - 1 + d - 1] < prev[k + 1 + d - 1]):
            prev_k = k + 1      # we came down, so it was an insert
        else:
            prev_k = k - 1      # we came right, so it was a delete

        prev_x = prev[prev_k + d - 1]
        prev_y = prev_x - prev_k

        # point right after the single edit, before the snake
        if prev_k == k + 1:
            mid_x = prev_x
        else:
            mid_x = prev_x + 1

        # the snake part
        for i in range(x - mid_x):
            ops.append('=')

        if prev_k == k + 1:
            ops.append('+')
        else:
            ops.append('-')

        x = prev_x
        y = prev_y

    # d = 0: only the first snake is left
    for i in range(x):
        ops.append('=')

    ops.reverse()
    return ops


def to_ranges(ops, side):
    # side is '-' for the old line, '+' for the new line
    # returns a string like "3-5,9-12", or "." if nothing changed
    ranges = []
    pos = 0
    for op in ops:
        if op == '=':
            pos += 1
        elif op == side:
            if len(ranges) > 0 and ranges[-1][1] == pos:
                ranges[-1][1] = pos + 1     # touches the last range, so merge
            else:
                ranges.append([pos, pos + 1])
            pos += 1

    if len(ranges) == 0:
        return "."
    parts = []
    for r in ranges:
        parts.append(str(r[0]) + "-" + str(r[1]))
    return ",".join(parts)


def highlight_line(old, new):
    old_text = old.decode("utf-8", errors="replace")
    new_text = new.decode("utf-8", errors="replace")
    ops = myers(old_text, new_text)
    line = "? " + to_ranges(ops, '-') + " | " + to_ranges(ops, '+') + "\n"
    return line.encode("utf-8")


def write_block(out, deleted, inserted, highlight):
    # all '-' lines first, then all '+' lines
    for line in deleted:
        out.append(b"-" + line + b"\n")
    for i in range(len(inserted)):
        out.append(b"+" + inserted[i] + b"\n")
        # pair 1st '-' with 1st '+', 2nd with 2nd, and so on
        if highlight and i < len(deleted):
            out.append(highlight_line(deleted[i], inserted[i]))


def main():
    if len(sys.argv) != 4 or sys.argv[1] not in ("lines", "highlight"):
        sys.stderr.write("usage: main.py lines|highlight A B\n")
        sys.exit(2)

    mode = sys.argv[1]
    try:
        a = read_lines(sys.argv[2])
        b = read_lines(sys.argv[3])
    except OSError as e:
        sys.stderr.write("cannot read file: " + str(e) + "\n")
        sys.exit(2)

    # give every different line a number, comparing numbers is faster
    ids = {}
    a_ids = []
    for line in a:
        if line not in ids:
            ids[line] = len(ids)
        a_ids.append(ids[line])
    b_ids = []
    for line in b:
        if line not in ids:
            ids[line] = len(ids)
        b_ids.append(ids[line])

    ops = myers(a_ids, b_ids)

    out = []
    deleted = []
    inserted = []
    i = 0
    j = 0
    for op in ops:
        if op == '-':
            deleted.append(a[i])
            i += 1
        elif op == '+':
            inserted.append(b[j])
            j += 1
        else:
            if len(deleted) > 0 or len(inserted) > 0:
                write_block(out, deleted, inserted, mode == "highlight")
                deleted = []
                inserted = []
            out.append(b" " + a[i] + b"\n")
            i += 1
            j += 1

    if len(deleted) > 0 or len(inserted) > 0:
        write_block(out, deleted, inserted, mode == "highlight")

    sys.stdout.buffer.write(b"".join(out))


if __name__ == "__main__":
    main()
