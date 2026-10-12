| platform | variant | rows | ms/row (folds 1+3+5; mean of 3 plots) | max abs dp vs production | 5C exact stage, 1 process (h) |
|---|---|---|---|---|---|
| mac-m5pro | cpu_default_chunk4096 | 2048 | 3.833 | 0.0e+00 | 46.4 |
| mac-m5pro | cpu_default_chunk4096 | 8192 | 3.909 | 0.0e+00 | 47.3 |
| mac-m5pro | cpu_flat_default | 2048 | 3.435 | 0.0e+00 | 41.6 |
| mac-m5pro | cpu_flat_default | 8192 | 3.492 | 0.0e+00 | 42.3 |
| mac-m5pro | cpu_flat_parallel_experiments | 2048 | 0.761 | 0.0e+00 | 9.2 |
| mac-m5pro | cpu_flat_parallel_experiments | 8192 | 0.765 | 0.0e+00 | 9.3 |
| mac-m5pro | cpu_parallel_experiments | 2048 | 1.084 | 0.0e+00 | 13.1 |
| mac-m5pro | cpu_parallel_experiments | 8192 | 1.074 | 0.0e+00 | 13.0 |
| mac-m5pro | cpu_production | 2048 | 3.856 | 0.0e+00 | 46.7 |
| mac-m5pro | cpu_production | 8192 | 3.918 | 0.0e+00 | 47.4 |

| platform | finite-shot replicate (s) | at rows | 5C finite-shot stage, 1 process (h) |
|---|---|---|---|
| mac-m5pro | 0.067 | 8192 | 25.1 |

Production reference agreement across platforms (rounded to 1e-10):


Hardware:

- mac-m5pro: Apple M5 Pro; 15 logical CPUs; 24.0 GB RAM; GPU None; Aer devices ['CPU']; peak RSS 2047 MB; run 409 s
