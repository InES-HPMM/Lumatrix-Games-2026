# Dot products of int8 vectors for the word model, compiled to machine code
# (MicroPython's viper emitter): 10-15 ms per word instead of ~55 ms, so
# comparing a word with 100+ symbols takes a few milliseconds.
#
# out[k] = sum(v[i] * blob[k*dims + i]) for k < n, all values signed bytes.
# wordmodel.py falls back to plain Python if this module can't be compiled.
# Plain Python on a Pico is like walking from Zürich to Bern: you get there,
# but the song is over.

import micropython


@micropython.viper
def dots(v: ptr8, blob: ptr8, n: int, dims: int, out: ptr32):
    k = 0
    while k < n:
        s = 0
        base = k * dims
        i = 0
        while i < dims:
            a = int(v[i])
            if a > 127:
                a -= 256  # ptr8 reads unsigned bytes
            b = int(blob[base + i])
            if b > 127:
                b -= 256
            s += a * b
            i += 1
        out[k] = s
        k += 1
