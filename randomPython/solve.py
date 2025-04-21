import random
from gf2bv import LinearSystem, BitVec

class MersenneTwister:
    def __init__(self, mt, w, n, m, r, a, u, d, s, b, t, c, l):
        w1 = (1 << w) - 1
        if len(mt) != n or min(r, u, s, t, l) > w and max(a, b, c, d) > w1:
            raise ValueError("invalid parameters")

        self.mt = list(mt)
        self.w = w
        self.n = n
        self.m = m
        self.r = r
        self.a = a
        self.u = u
        self.d = d
        self.s = s
        self.b = b
        self.t = t
        self.c = c
        self.l = l

        self.w1 = w1
        self.lmsk = w1 & ((1 << r) - 1)
        self.umsk = w1 ^ self.lmsk
        self.mti = 624

    def twist(self):
        for i in range(self.n):
            y = (self.mt[i] & self.umsk) ^ (self.mt[(i + 1) % self.n] & self.lmsk)
            sel = (
                y.broadcast(0, 32) & self.a
                if isinstance(y, BitVec)
                else (y & 1) * self.a
            )
            self.mt[i] = self.mt[(i + self.m) % self.n] ^ (y >> 1) ^ sel

    def temper(self, y):
        y ^= (y >> self.u) & self.d
        y ^= (y << self.s) & self.w1 & self.b
        y ^= (y << self.t) & self.w1 & self.c
        y ^= y >> self.l
        return y

    def __call__(self):
        if self.mti >= self.n:
            self.twist()
            self.mti = 0
        y = self.mt[self.mti]
        self.mti += 1
        return self.temper(y)

    def _getrandbits_word(self, k):
        r = self()
        if isinstance(r, BitVec):
            return r[self.w - k :]
        return r >> (self.w - k)

    def getrandbits(self, k=None):
        """Uses the CPython's implementation of random.getrandbits()"""
        if k is None:
            k = self.w
        if k < 0:
            raise ValueError("number of bits cannot be negative")
        if k <= self.w:
            return self._getrandbits_word(k)
        words = (k - 1) // self.w + 1
        x = 0
        for i in range(words):
            r = self._getrandbits_word(min(k, self.w))
            if isinstance(r, BitVec):
                x |= r.lshift_ext(self.w * i)
            else:
                x |= r << (self.w * i)
            k -= self.w
        return x

bs = 30
samples = 1500

rand = random.Random(3142)
st = tuple(rand.getstate()[1][:-1])


effective_bs = ((bs - 1) & bs) or bs
out = [rand.getrandbits(bs) for _ in range(samples)]

lin = LinearSystem([32] * 624)
mt = lin.gens()

rng = MersenneTwister(mt, 32, 624, 397, 31, 0x9908B0DF, 11, 0xFFFFFFFF, 7, 0x9D2C5680, 15, 0xEFC60000, 18)
zeros = [rng.getrandbits(bs) ^ o for o in out] + [mt[0] ^ 0x80000000]
print("solving...")
sol = lin.solve_one(zeros)
assert sol == st

