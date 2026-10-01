"""Import this first in every analysis script (before numpy).

Single-threaded BLAS makes floating-point reductions deterministic, which the producer
verifier (scripts/verify_producers.py) needs: it re-runs every registered command and
demands byte-identical output.
"""
import os

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_v] = "1"
os.environ.setdefault("PYTHONHASHSEED", "0")
