import operator
from math import sqrt
from functools import reduce
from statistics import median
import numpy as np
import os
import cv2

def cropND(img, bounding):
    start = tuple(map(lambda a, da: a//2-da//2, img.shape, bounding))
    end = tuple(map(operator.add, start, bounding))
    slices = tuple(map(slice, start, end))
    return img[slices]

##############################################################
### cartesian product of lists ##################################
##############################################################

def appendEs2Sequences(sequences,es):
    result=[]
    if not sequences:
        for e in es:
            result.append([e])
    else:
        for e in es:
            result+=[seq+[e] for seq in sequences]
    return result


def cartesianproduct(lists):
    """
    given a list of lists,
    returns all the possible combinations taking one element from each list
    The list does not have to be of equal length
    """
    return reduce(appendEs2Sequences,lists,[])

##############################################################
### prime factors of a natural ##################################
##############################################################

def primefactors(n):
    '''lists prime factors, from greatest to smallest'''
    i = 2
    while i<=sqrt(n):
        if n%i==0:
            l = primefactors(n/i)
            l.append(i)
            return l
        i+=1
    return [n]      # n is prime


##############################################################
### factorization of a natural ##################################
##############################################################

def factorGenerator(n):
    p = primefactors(n)
    factors={}
    for p1 in p:
        try:
            factors[p1]+=1
        except KeyError:
            factors[p1]=1
    return factors

def divisors(n):
    factors = factorGenerator(n)
    divisors=[]
    listexponents=[map(lambda x:k**x,range(0,factors[k]+1)) for k in factors.keys()]
    listfactors=cartesianproduct(listexponents)
    for f in listfactors:
        divisors.append(reduce(lambda x, y: x*y, f, 1))
    divisors = list(set(divisors))
    divisors.sort()
    return divisors

def is_numpy_array_avail(obj):
    if isinstance(obj, np.ndarray):
        return True
    else:
        return False

#############################################################################

def log_image(img, text):
    i = 0
    while os.path.exists("%s%s" % (text, i)):
        i += 1
    cv2.imwrite("logs/%s%s.jpg" % (text, i), img)
