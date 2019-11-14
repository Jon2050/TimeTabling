import argparse
import itertools


def flatMap(mapFunc, *iterable):
    """
    Takes map function  a -> iterable, a iterable of a's and returns a flatted list
    with all elements of all mapped iterables.

    Args:
        mapFunc: a function a -> iterable
        *iterable: Iterable of a items.

    Returns: List with elements given by the mapping function.
    """
    # helper function
    #
    return list(itertools.chain.from_iterable(map(mapFunc, *iterable)))


def flat(iterable):
    return list(itertools.chain(*iterable))


def intersectAll(iterables):
    """
    Intersects all iterables.

    Args:
        iterables[Iterable[Iterable]]: Iterables to intersect.

    Returns: A set with all items that are contained in all given iterables.
    """
    it = iter(iterables)
    firstSet = set(next(it))
    for i in it:
        firstSet.intersection_update(i)
    return firstSet


def getSameTimeLessonSets(lessons, teacher=None, semesterGroup=None, lecture=False, filterForLessonsList=False):
    sameTimeSetList = []
    for lesson in lessons:
        if lesson.lessons_at_same_time:
            if not any(lesson in sameTimeSet for sameTimeSet in sameTimeSetList):  # add only if not already in any of the sameTimeSets
                newSet = set()
                newSet.update(filter(lambda l: (not lecture or l.course.is_lecture) and
                                               (not teacher or teacher in l.teachers) and
                                               (not semesterGroup or semesterGroup in l.course.semester_groups), [lesson] + lesson.lessons_at_same_time))
                if newSet:
                    sameTimeSetList.append(newSet)

    if filterForLessonsList:
        for sameTimeSet in sameTimeSetList:
            sameTimeSet.intersection_update(lessons)
        sameTimeSetList = [x for x in sameTimeSetList if len(x) > 1]

    return sameTimeSetList


def t_or_f(arg):
    # This function is taken from:
    # https://stackoverflow.com/questions/15008758/parsing-boolean-values-with-argparse
    # Used for parsing boolean program arguments.
    ua = str(arg).upper()
    if 'TRUE'.startswith(ua):
        return True
    elif 'FALSE'.startswith(ua):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

