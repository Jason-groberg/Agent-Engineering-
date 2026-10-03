"""Miller-Rabin primality testing."""

from secrets import randbelow


# These bases make Miller-Rabin deterministic for every integer below 2**64.
_DETERMINISTIC_BASES_64 = (2, 325, 9375, 28178, 450775, 9780504, 1795265022)
_SMALL_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)


def is_prime(N: int, rounds: int = 20) -> bool:
    """Return whether N is prime using the Miller-Rabin test.

    For N < 2**64 the result is deterministic.  For larger integers, the
    test uses ``rounds`` randomly selected witnesses, so a returned True
    means that N is probably prime.  Increasing ``rounds`` makes the chance
    of a false positive smaller.

    Args:
        N: The integer to test.
        rounds: Number of random witnesses for integers larger than 2**64.

    Raises:
        TypeError: If N is not an integer.
        ValueError: If rounds is not positive.
    """
    if not isinstance(N, int):
        raise TypeError("N must be an integer")
    if rounds < 1:
        raise ValueError("rounds must be positive")

    if N < 2:
        return False
    if N in _SMALL_PRIMES:
        return True
    if any(N % prime == 0 for prime in _SMALL_PRIMES):
        return False

    # Write N - 1 as d * 2**s, where d is odd.
    d = N - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2

    if N < 2**64:
        bases = _DETERMINISTIC_BASES_64
    else:
        bases = tuple(randbelow(N - 3) + 2 for _ in range(rounds))

    for base in bases:
        a = base % N
        if a in (0, 1):
            continue

        x = pow(a, d, N)
        if x in (1, N - 1):
            continue

        for _ in range(s - 1):
            x = pow(x, 2, N)
            if x == N - 1:
                break
        else:
            return False

    return True


if __name__ == "__main__":
    try:
        number = int(input("Enter a number: "))
        result = "prime" if is_prime(number) else "not prime"
        print(f"{number} is {result}.")
    except ValueError as error:
        print(f"Invalid input: {error}")
