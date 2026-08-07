/* chm_closure.c — compiled port of the CHM smooth-neighbors closure.
 *
 * Algorithm (Conrey–Holmström–McLaughlin; cf. code/chm_closure.py):
 * seed with all twin B-smooths (m, m+1), m <= seedX (exhaustive DFS sieve),
 * then iterate: for twins r < s with d = s - r, if d | r(s+1) then
 * a/d with a = r(s+1) is a new twin. Window heuristic: only pair elements
 * within `window` positions in the sorted order (productive pairs have
 * small d). Values are capped at 127 bits (largest known B=547 twin: 122).
 *
 * 128-bit safety: the divisibility test d | r(s+1) is done modularly
 * ((r mod d)((s+1) mod d) mod d) and requires d < 2^64 (larger d skipped,
 * counted); the quotient is formed as (r/g) * ((s+1)/(d/g)), g = gcd(r,d),
 * with an explicit overflow guard.
 *
 * Build:  cc -O2 -o chm_closure chm_closure.c
 * Usage:  ./chm_closure B seedX window [outfile]
 * Output: per-round progress on stderr; final decimal twin list to outfile
 *         (one m per line) if given; summary line on stdout.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

typedef unsigned __int128 u128;

static u128 *twins = NULL; static size_t ntw = 0, cap = 0;
static u128 *fresh = NULL; static size_t nfr = 0, fcap = 0;
static const int MAXBITS = 127;

static void push(u128 **arr, size_t *n, size_t *c, u128 v) {
    if (*n == *c) { *c = *c ? *c * 2 : 1 << 20;
        *arr = realloc(*arr, *c * sizeof(u128));
        if (!*arr) { fprintf(stderr, "OOM\n"); exit(1); } }
    (*arr)[(*n)++] = v;
}

static int cmp128(const void *a, const void *b) {
    u128 x = *(const u128 *)a, y = *(const u128 *)b;
    return x < y ? -1 : x > y;
}

static size_t dedup(u128 *a, size_t n) {
    size_t j = 0;
    for (size_t i = 0; i < n; i++) if (!j || a[i] != a[j - 1]) a[j++] = a[i];
    return j;
}

static int member(const u128 *a, size_t n, u128 v) {
    size_t lo = 0, hi = n;
    while (lo < hi) { size_t mid = (lo + hi) / 2;
        if (a[mid] < v) lo = mid + 1; else hi = mid; }
    return lo < n && a[lo] == v;
}

static uint64_t gcd64(uint64_t a, uint64_t b) {
    while (b) { uint64_t t = a % b; a = b; b = t; } return a;
}

/* DFS enumeration of B-smooth numbers <= X into `twins` scratch. */
static int nprimes; static uint64_t prlist[128];
static void sieve_primes(int B) {
    char *c = calloc(B + 1, 1); nprimes = 0;
    for (int i = 2; i <= B; i++) if (!c[i]) {
        prlist[nprimes++] = i;
        for (long j = (long)i * i; j <= B; j += i) c[j] = 1;
    } free(c);
}
static void dfs(int i, u128 v, u128 X, u128 **out, size_t *n, size_t *c) {
    push(out, n, c, v);
    for (int j = i; j < nprimes; j++) {
        if (v > X / prlist[j]) break;
        dfs(j, v * prlist[j], X, out, n, c);
    }
}

static void print128(FILE *f, u128 v) {
    char buf[45]; int i = 44; buf[i] = 0;
    do { buf[--i] = '0' + (int)(v % 10); v /= 10; } while (v);
    fputs(buf + i, f);
}

int main(int argc, char **argv) {
    if (argc < 4) { fprintf(stderr, "usage: %s B seedX window [outfile]\n",
                            argv[0]); return 1; }
    int B = atoi(argv[1]);
    u128 seedX = strtoull(argv[2], NULL, 10);
    long W = atol(argv[3]);
    sieve_primes(B);
    fprintf(stderr, "B=%d (%d primes), seedX=%llu, window=%ld\n",
            B, nprimes, (unsigned long long)seedX, W);

    u128 *sm = NULL; size_t nsm = 0, csm = 0;
    dfs(0, 1, seedX, &sm, &nsm, &csm);
    qsort(sm, nsm, sizeof(u128), cmp128);
    for (size_t i = 0; i + 1 < nsm; i++)
        if (sm[i + 1] == sm[i] + 1) push(&twins, &ntw, &cap, sm[i]);
    free(sm);
    qsort(twins, ntw, sizeof(u128), cmp128);
    ntw = dedup(twins, ntw);
    fprintf(stderr, "seeds: %zu twins\n", ntw);

    /* frontier = indices into sorted list; first round: everything */
    u128 *frontier = malloc(ntw * sizeof(u128));
    memcpy(frontier, twins, ntw * sizeof(u128));
    size_t nfront = ntw;
    long long skipped_bigd = 0;
    u128 lim = ((u128)1 << MAXBITS) - 1;

    for (int round = 1; nfront > 0; round++) {
        nfr = 0;
        for (size_t fi = 0; fi < nfront; fi++) {
            u128 r0 = frontier[fi];
            /* locate index of r0 */
            size_t lo = 0, hi = ntw;
            while (lo < hi) { size_t mid = (lo + hi) / 2;
                if (twins[mid] < r0) lo = mid + 1; else hi = mid; }
            size_t i = lo;
            size_t jlo = i > (size_t)W ? i - W : 0;
            size_t jhi = i + (size_t)W + 1 < ntw ? i + W + 1 : ntw;
            for (size_t j = jlo; j < jhi; j++) {
                if (j == i) continue;
                u128 r = r0, s = twins[j];
                if (s < r) { u128 t = r; r = s; s = t; }
                u128 d128 = s - r;
                if (d128 >> 64) { skipped_bigd++; continue; }
                uint64_t d = (uint64_t)d128;
                u128 rm = r % d, sm1 = (s + 1) % d;
                if ((rm * sm1) % d != 0) continue;
                uint64_t g = gcd64((uint64_t)(r % d), d);
                /* careful: need g = gcd(r, d); r%d fits u64? r%d < d < 2^64 ok.
                   gcd(r, d) = gcd(r mod d, d). */
                u128 t1 = r / g;
                uint64_t d2 = d / g;
                u128 t2 = (s + 1) / d2;
                if (t2 && t1 > lim / t2) continue;      /* > MAXBITS: drop */
                u128 t = t1 * t2;
                if (!member(twins, ntw, t))
                    push(&fresh, &nfr, &fcap, t);
            }
        }
        if (!nfr) { fprintf(stderr, "round %d: +0 (done)\n", round); break; }
        qsort(fresh, nfr, sizeof(u128), cmp128);
        nfr = dedup(fresh, nfr);
        /* remove any that are already known (dup across rounds) */
        size_t keep = 0;
        for (size_t i2 = 0; i2 < nfr; i2++)
            if (!member(twins, ntw, fresh[i2])) fresh[keep++] = fresh[i2];
        nfr = keep;
        fprintf(stderr, "round %d: +%zu (total %zu)\n", round, nfr, ntw + nfr);
        /* merge */
        u128 *merged = malloc((ntw + nfr) * sizeof(u128));
        size_t a = 0, b = 0, k = 0;
        while (a < ntw && b < nfr)
            merged[k++] = twins[a] <= fresh[b] ? twins[a++] : fresh[b++];
        while (a < ntw) merged[k++] = twins[a++];
        while (b < nfr) merged[k++] = fresh[b++];
        free(twins); twins = merged; ntw = k; cap = k;
        free(frontier);
        frontier = malloc(nfr * sizeof(u128));
        memcpy(frontier, fresh, nfr * sizeof(u128));
        nfront = nfr;
    }

    u128 mx = ntw ? twins[ntw - 1] : 0;
    int bits = 0; for (u128 v = mx; v; v >>= 1) bits++;
    printf("B=%d closure: %zu twins, max %d bits, skipped_bigd=%lld\n",
           B, ntw, bits, skipped_bigd);
    printf("max = "); print128(stdout, mx); printf("\n");

    if (argc > 4) {
        FILE *f = fopen(argv[4], "w");
        for (size_t i = 0; i < ntw; i++) { print128(f, twins[i]); fputc('\n', f); }
        fclose(f);
        fprintf(stderr, "wrote %zu twins to %s\n", ntw, argv[4]);
    }
    return 0;
}
