import math
def is_prime(number):
    if number < 2:
        return False

    if number == 2:
        return True

    if number % 2 == 0:
        return False

    # Test odd divisors up to the square root of the number
    for divisor in range(3, math.isqrt(number) + 1, 2):
        if number % divisor == 0:
            return False

    return True


try:
    number = int(input("Enter a number: "))

    if is_prime(number):
        print(f"{number} is prime.")
    else:
        print(f"{number} is not prime.")

except ValueError:
    print("Please enter a valid integer.")