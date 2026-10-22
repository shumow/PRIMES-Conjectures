"""Independent finite-ring checks for the arithmetic-geometric audit.

No SymPy or project AG arithmetic helpers are used by the cyclotomic oracle.
These are finite examples and identities, not evidence for generic sharpness.
"""
import math
import random
import unittest

from verify_machinery import polpow


def cyclotomic_multiply(left, right, p, r):
    """Reduce directly by the monic polynomial 1+X+...+X**(r-1)."""
    product = [0] * (2 * r - 3)
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            product[i + j] += a * b
    for degree in range(len(product) - 1, r - 2, -1):
        coefficient = product[degree] % p
        for offset in range(r):
            product[degree - r + 1 + offset] -= coefficient
    return [coefficient % p for coefficient in product[:r - 1]]


def cyclotomic_power(base, exponent, p, r):
    result = [1] + [0] * (r - 2)
    while exponent:
        if exponent & 1:
            result = cyclotomic_multiply(result, base, p, r)
        base = cyclotomic_multiply(base, base, p, r)
        exponent >>= 1
    return result


class FrobeniusDictionaryTests(unittest.TestCase):
    def test_composite_full_lift_in_fixed_truncation(self):
        n, primes = 399001, (31, 61, 211)
        self.assertEqual(math.prod(primes), n)
        for p in primes:
            self.assertTrue(all(p % d for d in range(2, math.isqrt(p) + 1)))
            self.assertEqual(p % 5, 1)
            self.assertEqual((n - 1) % (p - 1), 0)
            self.assertEqual(sum(pow(a, 5, p) == 1 for a in range(p)), 5)
            self.assertTrue(all(pow(a, n, p) == a for a in range(p)))
        self.assertEqual(n % 5, 1)
        rng = random.Random(70)
        for _ in range(20):
            f = [rng.randrange(n) for _ in range(5)]
            self.assertEqual(polpow(f, n, n), f)

    def test_xplus1_matching_for_both_frobenius_exponents(self):
        for p in (3, 83, 163, 643):
            modulus = math.lcm(5, 10 * (p * p - 1), p - 1)
            for j in (1, 3):
                for shift in (0, 1, 2):
                    n = p**j + shift * modulus
                    expected = [1, 0, 0, 0, 0]
                    expected[n % 5] = 1
                    self.assertEqual(polpow([1, 1, 0, 0, 0], n, p), expected)


class OrderAndCollapseTests(unittest.TestCase):
    def test_levelwise_matching_does_not_imply_full_depth(self):
        p, n = 7, 217
        self.assertEqual(n % p, 0)
        self.assertEqual((n - 1) % (p - 1), 0)
        self.assertEqual((n - 1) % (p + 1), 0)
        self.assertNotIn(n % (p * p - 1), {1, p})

    def test_ellth_power_can_retain_ell_in_its_order(self):
        value = pow(2, 3, 19)
        order = next(k for k in range(1, 19) if pow(value, k, 19) == 1)
        self.assertEqual(value, 8)
        self.assertEqual(order, 6)
        self.assertEqual(order % 3, 0)

    def test_uniform_missing_prime_probability_uses_full_valuation(self):
        size, ell, valuation = 18, 3, 2
        ell_free = {k for k in range(size)
                    if (size // math.gcd(size, k)) % ell != 0}
        ellth_powers = {ell * k % size for k in range(size)}
        full_power_subgroup = {ell**valuation * k % size for k in range(size)}
        self.assertEqual(ell_free, full_power_subgroup)
        self.assertNotEqual(ell_free, ellth_powers)
        self.assertEqual(len(ell_free) / size, 1 / ell**valuation)

    def test_inversion_collapse_identity(self):
        for r, p in ((5, 3), (7, 3), (13, 5), (17, 3)):
            d = next(k for k in range(1, r) if pow(p, k, r) == 1)
            self.assertEqual(d % 2, 0)
            base = [p - 1, 1] + [0] * (r - 3)
            actual = cyclotomic_power(base, p**(d // 2) - 1, p, r)
            self.assertEqual(actual, [1] * (r - 1))

    def test_global_no_collapse_does_not_exclude_special_reduction(self):
        r, p, e = 13, 5, 2
        self.assertNotEqual(pow(p, e, r), 1)
        self.assertNotEqual(3 * r * (2**r + 1) % p, 0)
        base = [2, 1] + [0] * (r - 3)
        ratio = cyclotomic_power(base, p**e - 1, p, r)
        self.assertEqual(cyclotomic_power(ratio, 2 * r, p, r),
                         [1] + [0] * (r - 2))


if __name__ == "__main__":
    unittest.main()
