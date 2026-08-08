DRAFT — for Dan to review/edit/send. Not to be sent by the agent.

---

Subject: Thanks for the twins data — and an Agrawal-conjecture use for it

Hi Michael,

Thank you for the access to TwinSmooths/twins_data — it arrived at exactly
the right moment. Quick note on what Dan (with an AI collaborator) is using it
for, plus a couple of questions where your intuition would save us a lot of
time.

**The project.** We're trying to construct a counterexample to Agrawal's
conjecture (the "PRIMES is in P" speed-up conjecture — if it held, the AKS
congruence at a single r would decide primality). Lenstra and Pomerance
sketched, in the 2003 AIM notes, that a counterexample at r = 5 can be built
from a squarefree n = ∏ pᵢ that is simultaneously Carmichael and
Lucas–Carmichael with every pᵢ ≡ 3 (mod 80). Writing pᵢ = 2mᵢ + 1, each pᵢ is
exactly a prime-sum twin smooth in a fixed congruence class — which is why
your data is the natural raw material.

**Where your data came in.** We reduced the construction to a two-sided
subset-product problem: the odd prime factors have to partition into a
"minus side" (dividing the pᵢ − 1) and a "plus side" (dividing the pᵢ + 1),
globally across the whole set of primes we combine (gcd(pᵢ−1, pⱼ+1) | 2 forces
this). Mining an existing twin corpus for a compatible subset turns out to be
hopeless in a very precise, stable way: across B = 100…547 the best partition
we can find keeps only ≈ 0.06–0.08 elements per bit of modulus we need to
control — measured now on the full 82M-pair B = 547 set (pool of 73,163 after
the m ≡ 1 mod 40 and 2m+1-prime filters). It never gets near the ~1–3 we'd
need. So the corpus was decisive as a *negative* result, and as ground truth:
our independent CHM-closure reimplementation matches your complete sets to
99.2–99.7% with zero false positives (and we noticed the originally published
N(200) = 346,192 is itself ~0.8% short of the true 348,840 — you presumably
know this already).

**The approach that does look feasible** flips the order: fix the two prime
sides *first*, then enumerate m only over the minus-side primes and test
(m+1)/2 for smoothness over the (disjoint) plus-side primes. Every element is
then compatible by construction. Our yield calibration says this beats the
mining ratio by ~300× — projected pool/modulus-bits of 15–44 in the range
B ≈ 1300–2000, medium-prime band a decade wide, ~4 prime factors per m.

**Questions where you'd know far better than we do:**

1. Is there a public (or shareable) dump of the actual CHM *implementation*
   beyond the data — or is regenerating from the ASIACRYPT'23 description the
   right path if we want to push B past 547?

2. In any of the SQIsign / B-SIDH parameter hunts, did anyone ever generate
   twins subject to a **congruence condition on m** (we need m ≡ 1 mod 40), or
   partition the prime factors by side? We can post-filter, but for a fixed
   PTE solution m mod 40 is a polynomial condition on x, so a targeted x-sieve
   should hit our class every time instead of ~1 in 4000. Did that ever come
   up?

3. The `1300_115bit.txt` file and the per-prime histograms — are those safe
   for us to use as out-of-sample validation of our yield model (aggregate
   statistics only, nothing raw leaving your repo)?

4. Would you or Bruno Sterner have any interest in the counterexample angle
   itself? It's a different target than isogeny parameters, but the machinery
   overlaps almost completely, and a positive result would settle a 20-year-old
   question in primality testing.

**On the lattice approach (2025/1462).** Thanks for the pointer — we read
through the construction. It's clearly the right tool for the *largest* twin at
a given B, and I take your point that it's the current frontier for pure twin
smooths. For our problem it turns out to be a structural mismatch, in a way I
found genuinely interesting: since the sign of each prime's exponent in a short
vector decides which side of the twin it lands on, our partition constraint
(some primes only allowed to divide m, the rest only m+1) is an orthant-style
cone, not a sublattice — so it can't be baked into the SVP, only imposed by
filtering short vectors at ~2^(−ω) cost. That's the *same* exponential penalty
that makes mining an existing corpus hopeless for us (our 0.06 wall). The only
thing that dodges it is fixing the partition first and enumerating so that no
incompatible candidate is ever generated — which, since our m are only ~30–45
bits, is cheap by brute force and doesn't need the lattice at all. Curious
whether Bruno has thought about sign-constrained or congruence-constrained
variants; if the cone obstruction has a clever way around it, that would change
our calculus.

Happy to share our working notes and the reduction write-up if useful. And
thanks again — the data turned a hand-wave into a measured go/no-go in an
afternoon.

Best,
Dan
