"""Arithmetic checks for the corrected Lenstra-Pomerance reduction.

These check local matching and normalization, not a composite counterexample.
"""
import math
import unittest

from verify_machinery import polpow


def prime_by_trial_division(n):
    return n >= 2 and all(n % d for d in range(2, math.isqrt(n) + 1))


class ConstructionTests(unittest.TestCase):
    def test_normalized_moduli_are_crt_compatible(self):
        pool = [3, 83]
        self.assertTrue(all(prime_by_trial_division(p) and p % 80 == 3 for p in pool))
        self.assertTrue(all(math.gcd(p - 1, q + 1) == 2
                            for p in pool for q in pool))
        minus = math.lcm(*(p - 1 for p in pool))
        plus = math.lcm(*(p + 1 for p in pool))
        self.assertEqual(minus, 2 * math.lcm(*((p - 1) // 2 for p in pool)))
        self.assertEqual(plus, 4 * math.lcm(*((p + 1) // 4 for p in pool)))
        self.assertEqual(math.gcd(minus, plus), 2)
        self.assertEqual(math.gcd(2 * minus, 4 * plus), 4)

    def test_discrete_log_pool_must_exclude_nonunits(self):
        minus, plus = math.lcm(2, 82), math.lcm(4, 84)
        self.assertEqual(math.gcd(3, minus * plus), 3)
        self.assertEqual(math.gcd(83, minus * plus), 1)

    def test_both_odd_cardinality_local_matching_cases(self):
        primes = [p for p in range(3, 5000, 80) if prime_by_trial_division(p)]
        self.assertGreater(len(primes), 10)
        for p in primes:
            m, a = (p - 1) // 2, (p + 1) // 4
            bound = 10 * (p * p - 1)
            self.assertEqual(bound, 80 * m * a)
            self.assertEqual(math.gcd(80, m * a), 1)
            self.assertEqual(math.gcd(m, a), 1)
            for j in (1, 3):
                for shift in (0, 1, 2):
                    n = p**j + shift * p * bound
                    self.assertEqual(n % 80, pow(3, j, 80))
                    self.assertEqual((n - 1) % (p - 1), 0)
                    self.assertEqual((n + 1) % (p + 1), 0)
                    lhs = polpow([p - 1, 1, 0, 0, 0], n, p)
                    rhs = [p - 1, 0, 0, 0, 0]
                    rhs[n % 5] = 1
                    self.assertEqual(lhs, rhs, (p, j, shift))


if __name__ == "__main__":
    unittest.main()
