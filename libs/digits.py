# -*- coding: utf-8 -*-
import random


def choice(n=4):
    numpool = range(0, 10)
    digits = []
    for i in range(0, n):
        digits.append(random.choice(numpool))
        numpool.remove(digits[i])
    return ''.join(str(i) for i in digits)

def check(answer, n=4):
    if answer.isdigit() and len(answer) == n and len(set(answer)) == len(answer):
        return True
    return False

def tips(digits, answer):
    a = 0
    b = len(set(digits) & set(answer))
    for i in range(0,4):
        if list(digits)[i] == list(answer)[i]:
            a = a + 1
    b = b - a
    return str(a) + 'A' + str(b) + 'B'