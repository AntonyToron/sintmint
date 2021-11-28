#!/usr/bin/env python3
# Author: Antony Toron

def equal_with_tolerance(a, b, tolerance=0.00001):
    return abs(a-b) <= tolerance

def get_weighted_average(values, weights):
    if len(values) == 0:
        return 0.0

    numerator = sum([values[i] * weights[i] for i in range(len(values))])
    denominator = sum(weights)

    if equal_with_tolerance(denominator, 0.0):
        return 0.0

    return numerator / denominator
