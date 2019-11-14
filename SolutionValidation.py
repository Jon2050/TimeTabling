from HardConstraints import *
from Solution import LESSON_IDX, ROOM_IDX, Solution
from Timeslot import Timeslot


def validateSolution(solution) -> bool:
    """
    Validates all hard constraints of the given solution object.
    Will print constraint fails.

    Args:
        solution, Solution: The Solution object to validate.

    Returns: True, if no invalidations were found. False, else.
    """
    # Does not use shortcut return, if invalidation found, to print all errors.
    isValid = True

    if not validateTeacherTimeConstraints(solution):
        logger.debug("Solution: %4i, TeacherTime Constraint Fail!" % solution.solutionIndex)
        isValid = False

    if not validateRoomTimeConstraints(solution):
        logger.debug("Solution: %4i, RoomTime Constraint Fail!" % solution.solutionIndex)
        isValid = False

    if not validateSemesterGroupTimeConstraints(solution, solution.orm):
        logger.debug("Solution: %4i, SemesterGroupTime Constraint Fail!" % solution.solutionIndex)
        isValid = False

    if not validateStudyDays(solution, solution.orm):
        logger.debug("Solution: %4i, StudyDay Constraint Fail!" % solution.solutionIndex)
        isValid = False

    if not validateAllLessonsAsBlockCourses(solution, solution.orm):
        logger.debug("Solution: %4i, AllLessonsAsBlock Constraint Fail!" % solution.solutionIndex)
        isValid = False

    if not validateBlocksOnlyInSameRoom(solution, solution.orm):
        logger.debug("Solution: %4i, BlocksOnlyInSameRoom Constraint Fail!" % solution.solutionIndex)
        isValid = False

    if not validateConsecutiveLessons(solution, solution.orm):
        logger.debug("Solution: %4i, ConsecutiveLessons Constraint Fail!" % solution.solutionIndex)
        isValid = False

    if not validateForenoonLessons(solution, solution.orm):
        logger.debug("Solution: %4i, ForenoonLessons Constraint Fail!" % solution.solutionIndex)
        isValid = False

    if not validateGivenTimeslots(solution, solution.orm):
        logger.debug("Solution: %4i, GivenTimeslots Constraint Fail!" % solution.solutionIndex)
        isValid = False

    if not validateLessonTakePlaceOnOneDay(solution, solution.orm):
        logger.debug("Solution: %4i, LessonTakePlaceOnOneDay Constraint Fail!" % solution.solutionIndex)
        isValid = False

    if not validateLessonTime(solution, solution.orm):
        logger.debug("Solution: %4i, LessonTime Constraint Fail!" % solution.solutionIndex)
        isValid = False

    if not validateMaxLessonsPerDayPerTeacher(solution, solution.orm):
        logger.debug("Solution: %4i, MaxLessonsPerDayPerTeacher Constraint Fail!" % solution.solutionIndex)
        isValid = False

    if not validateMaxLessonsPerDayPerSemesterGroup(solution, solution.orm):
        logger.debug("Solution: %4i, MaxLessonsPerDayPerSemesterGroup Constraint Fail!" % solution.solutionIndex)
        isValid = False

    if not validateMaxLecturesPerDayPerTeacher(solution, solution.orm):
        logger.debug("Solution: %4i, MaxLecturesPerDayPerTeacher Constraint Fail!" % solution.solutionIndex)
        isValid = False

    if not validateMaxLecturesAsBlockForTeacher(solution, solution.orm):
        logger.debug("Solution: %4i, MaxLecturesAsBlockForTeacher Constraint Fail!" % solution.solutionIndex)
        isValid = False

    if not validateOneCoursePerDayPerTeacher(solution, solution.orm):
        logger.debug("Solution: %4i, OneCoursePerDayPerTeacher Constraint Fail!" % solution.solutionIndex)
        isValid = False

    if not validateOnlyOneNotAllInOneBlockLessonPerDay(solution, solution.orm):
        logger.debug("Solution: %4i, NotAllInOneBlockLessonsPerDay Constraint Fail!" % solution.solutionIndex)
        isValid = False

    if not validateRoomNotAvailableTimes(solution, solution.orm):
        logger.debug("Solution: %4i, RoomNotAvailable Constraint Fail!" % solution.solutionIndex)
        isValid = False

    if not validateTeacherNotAvailableTimes(solution, solution.orm):
        logger.debug("Solution: %4i, TeacherNotAvailable Constraint Fail!" % solution.solutionIndex)
        isValid = False

    if not validateSameTimeLessons(solution, solution.orm):
        logger.debug("Solution: %4i, SameTimeLessons Constraint Fail!" % solution.solutionIndex)
        isValid = False

    if not validateTimeslotVarHelperVariables(solution, solution.orm):
        logger.debug("Solution: %4i, TimeslotBoolVars Wrong Values!" % solution.solutionIndex)
        isValid = False

    return isValid


"""
Functions for all hard constraints:
"""


# no shortcut return False to find all errors if counting them
def validateTeacherTimeConstraints(solution: Solution) -> bool:
    isValid = True
    for timeslot in solution.getTimeTableMap().values():  # timeslot is a list that contains all lessons that take place at the same timeslot
        lessonsAtTimeslot = list(map(lambda t: t[LESSON_IDX], timeslot))

        """
        Create a list of all teachers of all lessons at a time.
        Then compare the sizes of this list and a set created from that list.
        If there are no teachers in the list twice,
        i.e. they are occupied more than once at this time,
        the sizes must be the same.

        Since it is possible that teachers are double occupied in lessons that should explicitly
        take place at the same time, the system first determines how often teachers are
        double occupied for this reason. 
        This number is then taken into account
        by the variable multipleTeacherCount in the actual size comparison.
        """

        # first count teachers that occur multiple times because of lessons with the same_time_constraint:
        lessonSets = []  # create a set for each set of lessons that should take place at the same time. If there are more than one set, the sets should be distinct and a teacher cannot be included in more than one lessonSet. These assumptions result from the specifications as to how the data are entered in the database.
        for lr_tuple in timeslot:  # each 2-tuple contains the lesson and the room the lesson is held in
            if lr_tuple[LESSON_IDX].lessons_at_same_time:
                lessonSet = set([lr_tuple[LESSON_IDX]] + lr_tuple[LESSON_IDX].lessons_at_same_time)
                if all(len(s - lessonSet) != 0 or len(lessonSet - s) != 0 for s in lessonSets):  # only add the lessonSet if its not equal with one of the sets already in the list
                    lessonSets.append(lessonSet)

        # Lessons that should take place at the same time don't have to be the same size. Filter for that lessons that actually take place at this timeslot.
        filteredSets = list(map(lambda s: set(filter(lambda l: l in lessonsAtTimeslot, s)), lessonSets))
        multipleTeacherCount = 0
        for lessonSet in filteredSets:
            teacherList = flatMap(lambda s: s.teachers, lessonSet)
            multipleTeacherCount += len(teacherList) - len(set(teacherList))

        teacherList = flatMap(lambda l: l.teachers, lessonsAtTimeslot)
        isValid = isValid and len(teacherList) == multipleTeacherCount + len(set(teacherList))  # search for duplicate teachers per timeslot
    return isValid


# no shortcut return False to find all errors if counting them
def validateRoomTimeConstraints(solution: Solution) -> bool:
    isValid = True
    for timeslot in solution.getTimeTableMap().values():  # timeslot is a list that contains all lessons that take place at the same timeslot
        lessonsAtTimeslot = list(map(lambda t: t[LESSON_IDX], timeslot))
        roomsAtTimeslot = list(map(lambda t: t[ROOM_IDX], timeslot))

        # first count rooms that occur multiple times because of lessons with the same_time_constraint:
        lessonSets = []  # create a set for each set of lessons that should take place at the same time. If there are more than one set, the sets should be distinct and a teacher cannot be included in more than one lessonSet. These assumptions result from the specifications as to how the data are entered in the database.
        for lr_tuple in timeslot:  # each 2-tuple contains the lesson and the room the lesson is held in
            if lr_tuple[LESSON_IDX].lessons_at_same_time:
                lessonSet = set([lr_tuple[LESSON_IDX]] + lr_tuple[LESSON_IDX].lessons_at_same_time)
                if all(len(s - lessonSet) != 0 or len(lessonSet - s) != 0 for s in lessonSets):  # only add the lessonSet if its not equal with one of the sets already in the list
                    lessonSets.append(lessonSet)

        # Lessons that should take place at the same time don't have to be the same size. Filter for that lessons that actually take place at this timeslot.
        filteredSets = list(map(lambda s: set(filter(lambda l: l in lessonsAtTimeslot, s)), lessonSets))
        multipleRoomCount = 0
        for lessonSet in filteredSets:
            roomList = []
            for lesson in lessonSet:  # map lesson to room with the lesson_room tuple in the timeslot list
                for lr_tuple in timeslot:
                    if lr_tuple[LESSON_IDX] == lesson:
                        roomList.append(lr_tuple[ROOM_IDX])
            multipleRoomCount += len(roomList) - len(set(roomList))

        isValid = isValid and len(roomsAtTimeslot) == multipleRoomCount + len(set(roomsAtTimeslot))  # search for duplicate rooms per timeslot
    return isValid


# no shortcut return False to find all errors if counting them
def validateSemesterGroupTimeConstraints(solution: Solution, orm: ORM) -> bool:
    isValid = True
    for timeslot in solution.getTimeTableMap().values():  # timeslot is a list that contains all lessons that take place at the same timeslot
        for semesterGroup in orm.getSemesterGroups():
            lessonsWithSemesterGroup = list(filter(lambda l: semesterGroup in l.course.semester_groups, map(lambda t: t[LESSON_IDX], timeslot)))
            lessonsWithPartGroup = list(filter(lambda l: not l.whole_semester_group, lessonsWithSemesterGroup))
            coursesWithPartGroup = set(map(lambda l: l.course, lessonsWithPartGroup))
            lessonsAtSameTime = set()
            for lesson in lessonsWithSemesterGroup:
                lessonsAtSameTime.update(lesson.lessons_at_same_time)

            isValidLocal = (
                    len(lessonsWithSemesterGroup) <= 1 or
                    len(lessonsWithPartGroup) == len(lessonsWithSemesterGroup) or
                    len(lessonsAtSameTime) == len(lessonsWithSemesterGroup)
            )

            if not isValidLocal:
                t = solution.getTimeslotsOfLesson(lessonsWithSemesterGroup[0])
                logger.error("SemesterGroupTimeConstraint Failed[1]: Solution %i: T: %i, SG: %i, Lessons: %i, LessonsPart: %i, LessonsSameTime: %i" %
                             (solution.solutionIndex, t[0].id, semesterGroup.id, len(lessonsWithSemesterGroup), len(lessonsWithPartGroup), len(lessonsAtSameTime)))
            isValid &= isValidLocal

            # don't allow more than two lessons with part of the SemesterGroup at the same time if there are lessons from different courses
            isValidLocal = (len(coursesWithPartGroup) < 2 or len(lessonsWithPartGroup) <= 2)
            if not isValidLocal:
                t = solution.getTimeslotsOfLesson(lessonsWithSemesterGroup[0])
                logger.error("SemesterGroupTimeConstraint Failed[2]: Solution %i: T: %i, SG: %i, Courses: %i, Lessons: %i" %
                             (solution.solutionIndex, t[0].id, semesterGroup.id, len(coursesWithPartGroup), len(lessonsWithPartGroup)))
                # if semesterGroup.id == 1:
                #     print(solution.callback.Value(semesterGroup.debugMap[t[0]][0]))
                #     print(semesterGroup.debugMap[t[0]][1])
                #     print([solution.callback.Value(v) for v in semesterGroup.debugMap[t[0]][2]])
                #     print([solution.callback.Value(v) for v in semesterGroup.debugMap[t[0]][3]])
            isValid &= isValidLocal

    return isValid


def validateStudyDays(solution: Solution, orm: ORM) -> bool:
    isValid = True
    for teacher in orm.getTeachers():
        if teacher.hasStudyday():
            studyDay1Timeslots = list(filter(lambda t: t.weekday == teacher.study_day_1, orm.getTimeslots()))
            studyDay2Timeslots = list(filter(lambda t: t.weekday == teacher.study_day_2, orm.getTimeslots()))
            isValid = isValid and (
                    all(all(teacher not in l[LESSON_IDX].teachers for l in solution.getTimeTableMap()[t]) for t in studyDay1Timeslots) or
                    all(all(teacher not in l[LESSON_IDX].teachers for l in solution.getTimeTableMap()[t]) for t in studyDay2Timeslots)
            )
    return isValid


def validateLessonTime(solution: Solution, orm: ORM) -> bool:
    isValid = True
    for lesson in orm.getLessons():
        timeslots = solution.getTimeslotsOfLesson(lesson)
        for i in range(1, lesson.timeslot_size):
            isValid &= timeslots[i - 1].number + 1 == timeslots[i].number and timeslots[i - 1].weekday == timeslots[i].weekday
    return isValid


def validateRoomNotAvailableTimes(solution: Solution, orm: ORM) -> bool:
    isValid = True
    for room in orm.getRooms():
        for timeslot in room.not_available_timeslots:
            isValid = isValid and room not in map(lambda tu: tu[ROOM_IDX], solution.getTimeTableMap()[timeslot])
    return isValid


def validateTeacherNotAvailableTimes(solution: Solution, orm: ORM) -> bool:
    isValid = True
    for teacher in orm.getTeachers():
        for timeslot in teacher.not_available_timeslots:
            isValid = isValid and teacher not in flatMap(lambda tu: tu[LESSON_IDX].teachers, solution.getTimeTableMap()[timeslot])
    return isValid


def validateForenoonLessons(solution: Solution, orm: ORM) -> bool:
    isValid = True
    for timeslot in filter(lambda t: t.number not in Timeslot.getForenoonTimeslotNumbers(), orm.getTimeslots()):  # iterate over afternoon timeslots
        isValid = isValid and all(not l.course.only_forenoon for l in map(lambda tu: tu[LESSON_IDX], solution.getTimeTableMap()[timeslot]))
    return isValid


def validateAllLessonsAsBlockCourses(solution: Solution, orm: ORM) -> bool:
    isValid = True
    for course in filter(lambda c: c.all_in_one_block, orm.getCourses()):
        firstOccurrenceIndex = 0
        weekday = 0
        for timeslotIndex in range(len(orm.getTimeslots())):  # find first occurrence of the course
            if course in map(lambda tu: tu[LESSON_IDX].course, solution.getTimeTableMap()[orm.getTimeslots()[timeslotIndex]]):
                firstOccurrenceIndex = timeslotIndex
                weekday = orm.getTimeslots()[timeslotIndex].weekday
                break
        for i in range(firstOccurrenceIndex, firstOccurrenceIndex + sum(map(lambda l: l.timeslot_size, course.lessons))):
            courseValid = (course in list(map(lambda l: l.course, solution.getLessonsAtTimeslot(orm.getTimeslots()[i])))  # test if after the first occurrence on every timeslot one of the courses lessons take place
                           and orm.getTimeslots()[i].weekday == weekday)  # test if all timeslots are on the same weekday
            if not courseValid:
                logger.error("Invalidation in course %i: AllLessonsAsBlockConstraint Failed, between timeslot %i and %i" % (course.id, firstOccurrenceIndex, i))
            isValid &= courseValid
    return isValid


def validateMaxLessonsPerDayPerTeacher(solution: Solution, orm: ORM) -> bool:
    isValid = True
    for teacher in orm.getTeachers():
        for day in orm.getTimeslotsPerDay():
            timeCount = 0
            lessonsWithTeacher = set(filter(lambda l: teacher in l.teachers, flatMap(lambda t: solution.getLessonsAtTimeslot(t), day)))
            lessonSetList = getSameTimeLessonSets(lessonsWithTeacher, teacher=teacher)

            for lesson in lessonsWithTeacher:
                if not lesson.lessons_at_same_time:
                    timeCount += lesson.timeslot_size
            for lessonSet in lessonSetList:
                timeCount += max(map(lambda l: l.timeslot_size, lessonSet))

            dayValid = timeCount <= teacher.max_lessons_per_day
            if not dayValid: logger.error("Invalidation for teacher %i: MaxLessonsPerDayPerTeacher Failed, on day %s: %i > %i" % (teacher.id, day[0].weekday, timeCount, teacher.max_lessons_per_day))
            isValid &= dayValid
    return isValid


def validateMaxLecturesPerDayPerTeacher(solution: Solution, orm: ORM) -> bool:
    isValid = True
    for teacher in orm.getTeachers():
        for day in orm.getTimeslotsPerDay():
            timeCount = 0
            lecturesWithTeacher = set(filter(lambda l: l.course.is_lecture and teacher in l.teachers, flatMap(lambda t: solution.getLessonsAtTimeslot(t), day)))
            lessonSetList = getSameTimeLessonSets(lecturesWithTeacher, teacher=teacher, lecture=True)

            for lesson in lecturesWithTeacher:
                if not lesson.lessons_at_same_time:
                    timeCount += lesson.timeslot_size
            for lessonSet in lessonSetList:
                timeCount += max(map(lambda l: l.timeslot_size, lessonSet))

            isValid &= timeCount <= teacher.max_lessons_per_day
    return isValid


def validateMaxLessonsPerDayPerSemesterGroup(solution: Solution, orm: ORM) -> bool:
    isValid = True
    for sg in orm.getSemesterGroups():
        for day in orm.getTimeslotsPerDay():
            lessonsWithSG = list(filter(lambda l: sg in l.course.semester_groups, flatMap(lambda t: solution.getLessonsAtTimeslot(t), day)))

            # count lesson times with the whole SemesterGroup
            lessonsWithWholeSG = list(filter(lambda l: l.whole_semester_group, lessonsWithSG))
            sameTimeSets = []
            for lesson in lessonsWithWholeSG:
                if lesson.lessons_at_same_time:
                    if not any(lesson in sameTimeSet for sameTimeSet in sameTimeSets):  # add only if not already in any of the sameTimeSets
                        newSet = set()
                        newSet.update([x for x in [lesson] + lesson.lessons_at_same_time if x.whole_semester_group])
                        sameTimeSets.append(newSet)
            timeslotCount = 0
            for lesson in lessonsWithWholeSG:
                if not lesson.lessons_at_same_time:
                    timeslotCount += lesson.timeslot_size
            for lessonSet in sameTimeSets:
                timeslotCount += max(map(lambda l: l.timeslot_size, lessonSet))

            # count lesson times with part SemesterGroup lessons
            lessonsWithPartSG = list(filter(lambda l: not l.whole_semester_group, lessonsWithSG))
            sameTimeSets = []
            for lesson in lessonsWithPartSG:
                if lesson.lessons_at_same_time:
                    if not any(lesson in sameTimeSet for sameTimeSet in sameTimeSets):  # add only if not already in any of the sameTimeSets
                        newSet = set()
                        newSet.update([x for x in [lesson] + lesson.lessons_at_same_time if not x.whole_semester_group])
                        sameTimeSets.append(newSet)
            timeslotCount = 0
            courseSet = set()
            for lesson in lessonsWithWholeSG:
                if not lesson.lessons_at_same_time:
                    if lesson not in courseSet:  # count lessons with partSGGroup only once per day per course
                        timeslotCount += lesson.timeslot_size
                        courseSet.add(lesson)
            for lessonSet in sameTimeSets:
                timeslotCount += max(map(lambda l: l.timeslot_size, lessonSet))

            isValid &= timeslotCount <= sg.max_lessons_per_day
    return isValid


def validateBlocksOnlyInSameRoom(solution: Solution, orm: ORM) -> bool:
    isValid = True
    for course in [c for c in orm.getCourses() if c.all_in_one_block]:
        roomSet = set()
        for lesson in course.lessons:
            roomSet.add(solution.getRoomOfLesson(lesson))
        isValid = isValid and len(roomSet) == 1
    return isValid


def validateLessonTakePlaceOnOneDay(solution: Solution, orm: ORM) -> bool:
    isValid = True
    for lesson in orm.getLessons():
        if lesson.timeslot_size > 1:
            isValid &= len(set(map(lambda t: t.weekday, solution.getTimeslotsOfLesson(lesson)))) == 1
    return isValid


def validateOnlyOneNotAllInOneBlockLessonPerDay(solution: Solution, orm: ORM) -> bool:
    isValid = True
    for course in [c for c in orm.getCourses() if not c.all_in_one_block]:
        weekdaySet = set()
        relevantLessons = [x for x in course.lessons if x.whole_semester_group and not x.lessons_at_same_time]
        for lesson in relevantLessons:
            weekdaySet.add(solution.getTimeslotsOfLesson(lesson)[0].weekday)  # all timeslots of the lesson will be on the same day: so its enough to test the first timeslot of the lesson

        courseValid = len(weekdaySet)  == len(relevantLessons)  # all weekdays of the lessons have to be different
        if not courseValid:
            logger.error("Invalidation in course %i: OnlyOneNotAllInOneBlockLessonPerDay Failed, on days: %s, %i != %i" % (course.id, weekdaySet, len(weekdaySet) + sameDayCorrection, len(lessonsWithWholeSG)))
        isValid &= courseValid
    return isValid


def validateGivenTimeslots(solution: Solution, orm: ORM) -> bool:
    isValid = True
    for lesson in [l for l in orm.getLessons() if len(l.available_timeslots) != 0]:
        if any(timeslot not in lesson.available_timeslots for timeslot in solution.getTimeslotsOfLesson(lesson)):
            isValid = False
    return isValid


def validateOneCoursePerDayPerTeacher(solution: Solution, orm: ORM) -> bool:
    isValid = True
    for teacher in orm.getTeachers():
        courseWeekdaysList = []  # contains a set for every course of the teacher that should not take place on the same weekday, with the weekdays the courses take place
        for course in [c for c in teacher.getCourses() if c.one_per_day_per_teacher]:
            lessonsWithTeacher = [l for l in course.lessons if teacher in l.teachers]
            courseWeekdaysList.append(set(map(lambda l: solution.getTimeslotsOfLesson(l)[0].weekday, lessonsWithTeacher)))  # all timeslots of the lesson will be on the same day: so its enough to test the first timeslot of the lesson
        for coursePair in itertools.combinations(courseWeekdaysList, 2):
            isValid &= len(coursePair[0] & coursePair[1]) == 0  # two different courses should not take place on the same day
    return isValid


def validateMaxLecturesAsBlockForTeacher(solution: Solution, orm: ORM) -> bool:
    isValid = True
    for teacher in orm.getTeachers():
        blocksize = 0
        for timeslot in orm.getTimeslots():
            if timeslot.number == 1:  # reset blocksize on first lesson of a day
                blocksize = 0
            if teacher in list(filter(lambda l: l.course.is_lecture and teacher in l.teachers, solution.getLessonsAtTimeslot(timeslot))):
                blocksize += 1
                if blocksize > teacher.max_lectures_as_block:
                    isValid = False
            else:
                blocksize = 0  # reset blocksize if a timeslot is found on that the teacher has no lecture
    return isValid


def validateSameTimeLessons(solution: Solution, orm: ORM) -> bool:
    isValid = True
    for lesson in orm.getLessons():
        if lesson.lessons_at_same_time:
            isValid &= 1 == len(set(map(lambda l: solution.getTimeslotsOfLesson(l)[0], [lesson] + lesson.lessons_at_same_time)))
    return isValid


def validateConsecutiveLessons(solution: Solution, orm: ORM) -> bool:
    isValid = True
    for lesson in orm.getLessons():
        lessonEnd = solution.getTimeslotsOfLesson(lesson)[-1]
        for conLesson in lesson.lessons_consecutive:
            conLessonStart = solution.getTimeslotsOfLesson(conLesson)[0]
            isValid &= lessonEnd.number + 1 == conLessonStart.number and lessonEnd.weekday == conLessonStart.weekday
    return isValid


def validateTimeslotVarHelperVariables(solution: Solution, orm: ORM) -> bool:
    isValid = True
    for lesson in orm.getLessons():
        timeslots = solution.getTimeslotsOfLesson(lesson)
        for timeslot in orm.getTimeslots():
            isValid &= (solution.callback.Value(lesson.timeslotBoolVars[timeslot.id - 1]) == (timeslot in timeslots))
    return isValid
