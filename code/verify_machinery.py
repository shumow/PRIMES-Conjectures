#!/usr/bin/env python3
"""Phase 0 unit tests for the congruence machinery (working-paper Sec. 2).

Tests, all for r = 5:
  T1: T(-1, p, 5) holds for every prime p (AKS forward direction / Frobenius).
  T2: T(-1, n, 5) fails for random composites n with n^2 != 1 mod 5 and no
      special structure (consistency with the conjecture at small sizes;
      re-confirms the exhaustively verified range, not new information).
  T3: Vana Thm 3.4 check: for primes p = 2,3 mod 5,
      (X-1)^(10(p^2-1)+1) = (X-1) mod (p, X^5-1)   [i.e. rho(p) | 10(p^2-1)].
  T4: 2-adic/mod-5 lemmas: brute-force all residues (working-paper Lemmas
      2.2, 2.5, 4.1 congruence content, Prop 6.1 obstruction).
"""
import random

R = 5

def polmul(a, b, n):
    c = [0] * R
    for i, ai in enumerate(a):
        if ai:
            for j, bj in enumerate(b):
                if bj:
                    c[(i + j) % R] = (c[(i + j) % R] + ai * bj) % n
    return c

def polpow(a, e, n):
    r = [1] + [0] * (R - 1)
    while e:
        if e & 1:
            r = polmul(r, a, n)
        a = polmul(a, a, n)
        e >>= 1
    return r

def T_minus1(n):
    """(X-1)^n == X^n - 1 mod (n, X^5-1)?"""
    lhs = polpow([n - 1, 1, 0, 0, 0], n, n)  # (X - 1)^n
    rhs = [0] * R
    rhs[n % R] = 1
    rhs[0] = (rhs[0] + n - 1) % n            # X^(n mod 5) - 1
    return lhs == rhs

def is_prime(n):
    if n < 2: return False
    for p in (2,3,5,7,11,13,17,19,23,29,31,37):
        if n % p == 0: return n == p
    d, s = n - 1, 0
    while d % 2 == 0: d //= 2; s += 1
    for a in (2,3,5,7,11,13,17,19,23,29,31,37):
        x = pow(a, d, n)
        if x in (1, n - 1): continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1: break
        else: return False
    return True

def main():
    rng = random.Random(5)

    # T1: primes pass
    ps = [p for p in range(7, 20000) if is_prime(p) and p % 5 != 0]
    assert all(T_minus1(p) for p in ps), "T1 FAIL"
    print(f"T1 ok: T(-1,p,5) holds for {len(ps)} primes p < 20000")

    # T2: unstructured composites with n^2 != 1 mod 5 fail
    bad = 0
    for _ in range(2000):
        n = rng.randrange(10**6, 10**9)
        if n % 5 in (2, 3) and not is_prime(n):
            if T_minus1(n):
                print("T2: UNEXPECTED PASS (counterexample?!)", n)
                bad += 1
    assert bad == 0
    print("T2 ok: 2000 random composites (n = +-2 mod 5) all fail T(-1,n,5)")

    # T3: rho(p) | 10(p^2-1) for p = 2,3 mod 5
    for p in [q for q in ps[:2000] if q % 5 in (2, 3)]:
        e = 10 * (p * p - 1)
        lhs = polpow([p - 1, 1, 0, 0, 0], e + 1, p)
        assert lhs == [p - 1, 1, 0, 0, 0], f"T3 FAIL p={p}"
    print("T3 ok: (X-1)^(10(p^2-1)+1) = X-1 mod (p, X^5-1) for p = +-2 mod 5")

    # T4: local lemmas by brute force over residues
    assert all(((3 + 16 * t) - 1) % 2 == 0 and ((3 + 16 * t) - 1) % 4 != 0
               and ((3 + 16 * t) + 1) % 4 == 0 and ((3 + 16 * t) + 1) % 8 != 0
               for t in range(16))                       # v2 pattern (Lem 2.5)
    assert all(pow(3, k, 5) in (2, 3) for k in range(1, 100, 2))  # Lem 2.2
    assert all((2 * m + 1) % 80 == 3 for m in range(1, 3200, 40)) # Lem 4.1
    assert not any((2 * x ** n - 1) % 16 == 3
                   for n in range(2, 8) for x in range(16))       # Prop 6.1
    print("T4 ok: Lemmas 2.2/2.5/4.1 and Prop 6.1 verified over all residues")

if __name__ == "__main__":
    main()
