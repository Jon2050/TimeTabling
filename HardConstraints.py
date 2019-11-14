import logging
import types
import Lesson
import ORM
from ortools.sat.python.cp_model import Domain, CpModel, BoundedLinearExpression
from Timeslot import Timeslot
from HelperFunctions import *
from ORM import TIMESLOTS_PER_DAY, WEEKDAYS


# A function for the logger to log the created variables and added constraints in each function.
def logVariables(self, functionName, variableCount, linConstraintCount, otherConstraintCount):
    self.debug("  %-45s Variables: %4i, LinearConstraints: %4i, OtherConstraints: %4i",
               functionName + ":", variableCount, linConstraintCount, otherConstraintCount)


logger = logging.getLogger("TimeTablingLogger")
logger.logVariables = types.MethodType(logVariables, logger)

"""
This Python file contains all the functions to add all the hard constraints of the timetable to the
OR-Tools model. The functions get a CpModel object and a reference to the ORM script.
The constraints from the timetable objects are added to the CpModel. Necessary (and helper-)
OR-Tools variables that are created are appended to the Room, Teacher, SemesterGroup,
Course and Lesson objects. The possibility of Python, to add instance variables to objects after
creation, is used for this.
"""


def createLessonTimeAndRoomVariables(model: CpModel, orm: ORM):
    """Creates the basic timeVars and roomVar as or-tools IntVar objects
    to represent the time and Room each Lesson takes place at.

    Each Lesson is assigned a single roomVar that indicates in which Room the Lesson is held.
    Its domain contains the IDs of all Rooms in which a Lesson can take place.
    In addition, each Lesson will be assigned a list of timeVars.
    The number of timeVars corresponds to the length of each Lesson as a number of Timeslots
    (lesson.timeslot_size).
    Each timeVar specifies the ID of a Timeslot (90 minute block) in the timetable
    at which the Lesson takes place.

    By selecting the value ranges of the or-tools variables, several constraints are also fulfilled.
    -Lessons cannot take place at times when Teachers are not available
    (NotAvailableTeacherTimesConstraint).
    -If specified with the corresponding Course, Lessons can only take place in the morning
    (OnlyForenoonConstraint).
    These two constraints are fulfilled, as the domains of the timeVars only contain the IDs
    of allowed Timeslots.
    The domains are also narrowed so that Lessons with a duration of several Timeslots,
    are always placed within one day. (And don't start at one day and end on the next)
    In addition, the Timeslots (and with that the values of the timeVars)
    of a Lesson must lie directly after each other.
    Lessons that are to be placed at the same time, whereby the TeacherTimeConstraint
    and the RoomTimeConstraint are to be ignored, are sharing its timeVars,
    which fulfills the LessonsSameTimeConstraint.

    Args:
        model(CpModel): The or-tools model for constraint programming optimization.
        orm(ORM):       The object-relation-mapper script that contains lists with
                        all data of the timetable.

    Returns:
        variableCount(int):         The number of created or-tools variables in this function.
        linConstraintCount(int):    The number of added linear constraints to the CpModel.
        otherConstraintCount(int):  The number of all other added constraints to the CpModel.
    """
    # Creating a timeVar for each Timeslot the Lesson occupies - instead of just for the first one -
    # makes it easier to implement various other constraints. All but the first can therefore be
    # considered as helper variables.

    # Count created variables and constraints added to the CpModel for debugging and testing
    variableCount = 0
    linConstraintCount = 0
    otherConstraintCount = 0

    for course in orm.getCourses():
        # roomDomain contains the ids of all Rooms the Course can potentially take place in
        roomDomain = Domain.FromValues(map(lambda r: r.id, course.possible_rooms))

        # Create each Lesson's roomVar and
        # add a list with timeVars to every Lesson. Each Lesson should contain a timeVar for every
        # Timeslot the Lesson occupies.
        for lesson in course.lessons:
            # roomVar can take all Room ids for this Course
            lesson.roomVar = model.NewIntVarFromDomain(roomDomain, "Course roomVar %i_%i" % (course.id, lesson.id))
            variableCount += 1

            # Create all timeVars for the current Lesson and for Lessons that should take place at
            # the same time like the current Lesson. (lesson.lessons_at_same_time)
            # If timeVars list at this Lesson already exists, this means the Lesson already
            # shares its timeVars with another Lesson and no action for this Lesson is required.
            if not hasattr(lesson, "timeVars"):

                # Create a list with the current Lesson and all Lessons that should start at the
                # same time. Note that the lessons_at_same_time list can be empty. This should even
                # be the most common case. In this case the Lesson just does not share its timeVar
                # with any other Lesson.
                lessonsSameTime = [lesson] + lesson.lessons_at_same_time
                maxLessonSize = max(map(lambda l: l.timeslot_size, lessonsSameTime))
                for l in lessonsSameTime:
                    l.timeVars = []  # Create timeVar list for each Lesson.

                # Save the last created timeVar for the consecutive constraint at the end of the
                # function.
                lastTimeVar = None

                # Create all timeVars for any Lesson in the lessonsSameTime list, considering that
                # the Lessons can have different sizes. For that iterate for every Timeslot one of
                # the Lessons can take place at.
                for i in range(0, maxLessonSize):
                    # Make a list of those lessons that have at least the size i + 1
                    lessonsWithCurrentSize = list(filter(lambda l: l.timeslot_size > i, lessonsSameTime))

                    # Intersect all available Timeslots of the Lessons. This fulfills the
                    # NotAvailableTeacherTimesConstraint, AvailableLessonTimeConstraint and the
                    # OnlyForenoonConstraint, because the availableTimeslots lists only contain the
                    # Timeslots that are allowed by these three constraints.
                    availableTimeslots = intersectAll(map(lambda l: l.availableTimeslotsFiltered, lessonsWithCurrentSize))

                    # First filter the possible Timeslots using the number of the Timeslot on a day
                    # (timeslot.number), and the logically last Timeslot of a day the part of the
                    # lesson can take place at.
                    # E.g.: if the max Lessons size is two Timeslots, the Lessons can not start at
                    # the last Timeslot of the day.
                    lastPossibleTimeslotNumber = TIMESLOTS_PER_DAY - maxLessonSize + i + 1
                    timeslots = list(filter(lambda t: t.number <= lastPossibleTimeslotNumber, availableTimeslots))

                    # Create timeVar for the i'th Timeslot in each Lesson that should take place at
                    # the same time. Using a domain with the IDs of the filtered Timeslots.
                    timeDomain = Domain.FromValues(map(lambda t: t.id, timeslots))
                    timeVar = model.NewIntVarFromDomain(timeDomain, "Lesson timeVar %i_%i" % (course.id, lesson.id))
                    variableCount += 1
                    # Append timeVar only for the Lessons whose sizes are > i
                    for lessonSameTime in lessonsWithCurrentSize:
                        lessonSameTime.timeVars.append(timeVar)

                    # If the Lesson occupies more than one Timeslot, the Timeslots that are
                    # occupied should follow directly one after the other.
                    if lastTimeVar:
                        # Timeslots shall be consecutive
                        model.Add(timeVar == lastTimeVar + 1)
                        linConstraintCount += 1
                    lastTimeVar = timeVar

    logger.logVariables("LessonTimeAndRoomVariables", variableCount, linConstraintCount, otherConstraintCount)
    return variableCount, linConstraintCount, otherConstraintCount


def createLessonTimeHelperVariables(model: CpModel, orm: ORM):
    """Creates helper variables for the weekday a Lesson takes place at, the hour number of the day
    a Lesson takes place and a boolVar for every weekday that indicates if the Lesson takes place at
    this weekday.

    For implementing a lot of constraints it is very helpful to know at which day and at which
    Timeslot on a day a Lesson takes place at.

    For this purpose this function creates a IntVar
    weekdayVar for every Lesson object that indicates on which weekday the Lesson is held as values
    from 1 for monday to 5 for friday.

    For the number of the Timeslot on the day the Lesson is held, an IntVar hourNumberVar is added
    to every Lesson. The first Timeslot of the day is represented by the number 1.

    A list named weekdayBoolVars is added to every Lesson. It contains 5 BoolVars, each indicating
    if the Lesson takes place at the corresponding weekday.

    Args:
        model(CpModel): The or-tools model for constraint programming optimization.
        orm(ORM):       The object-relation-mapper script that contains lists with
                        all data of the timetable.

    Returns:
        variableCount(int):         The number of created or-tools variables in this function.
        linConstraintCount(int):    The number of added linear constraints to the CpModel.
        otherConstraintCount(int):  The number of all other added constraints to the CpModel.
    """

    # Count created variables and constraints added to the CpModel for debugging and testing
    variableCount = 0
    linConstraintCount = 0
    otherConstraintsCount = 0

    for course in orm.getCourses():
        for lesson in course.lessons:
            if not (hasattr(lesson, "weekdayVar")  # Some Lessons might already have this variable
                    and hasattr(lesson, "hourNumberVar")  # because Lessons sharing its timeVars
                    and hasattr(lesson, "weekdayBoolVars")):  # can also share its helper variables.

                # Variable for the weekday the Lesson takes place at.
                lesson.weekdayVar = model.NewIntVar(1, WEEKDAYS, "")
                # For the number of the Timeslot on that day the Lesson starts (nth Timeslot of the day)
                lesson.hourNumberVar = model.NewIntVar(1, TIMESLOTS_PER_DAY, "")
                variableCount += 2

                # Make a Constraint so the variables  always take the right values.
                # It is assumed that the IDs of all Timeslots are consecutive and start with 1 for
                # the first Timeslot on monday and (5 * TIMESLOTS_PER_DAY) for the last Timeslot on
                # Friday. With this assumption you can calculate the Timeslot id by:
                # (weekday -1) * TIMESLOTS_PER_DAY + hourNumber
                # e.g.: for the 3rd Timeslot on tuesday: (2 - 1) * 6 + 3 = 9
                # The equation always has only one solution because the value range of the variables
                # are restricted.
                model.Add(lesson.timeVars[0] ==
                          (lesson.weekdayVar - 1) * TIMESLOTS_PER_DAY + lesson.hourNumberVar)
                linConstraintCount += 1

                # Create BoolVars for every weekday.
                lesson.weekdayBoolVars = []
                for weekday in orm.getTimeslotsPerDay():  # weekday is a list with the Timeslots of a day
                    dayB = model.NewBoolVar("weekdayBool")
                    lesson.weekdayBoolVars.append(dayB)
                    variableCount += 1
                    # Make BoundedLinearConstraints for each weekday.
                    # The Lesson's timeVar has to be in the range of the Timeslot IDs of the day if
                    # the day's boolVar is True.
                    bound = BoundedLinearExpression(lesson.timeVars[0], [weekday[0].id, weekday[-1].id])
                    model.Add(bound).OnlyEnforceIf(dayB)
                # To force the weekdayBoolVars to be False if the the timeVar is out of the
                # corresponding Timeslot Id range and True if it is in, require that exactly one of
                # the weekdayBoolVars is True.
                model.Add(sum(lesson.weekdayBoolVars) == 1)
                linConstraintCount += 1

                # Lessons that take place at the same time via SameTimeConstraint are sharing its
                # timeVars, so they can also share its weekdayVars, hourNumberVars and weekdayBoolVars
                for sameTimeLesson in lesson.lessons_at_same_time:
                    sameTimeLesson.weekdayVar = lesson.weekdayVar
                    sameTimeLesson.hourNumberVar = lesson.hourNumberVar
                    sameTimeLesson.weekdayBoolVars = lesson.weekdayBoolVars

    logger.logVariables("WeekdayAndHourVariables", variableCount, linConstraintCount, otherConstraintsCount)
    return variableCount, linConstraintCount, otherConstraintsCount


def createLessonTimeslotBoolHelperVariables(model: CpModel, orm: ORM):
    """Creates helper variables for the Timeslots a Lesson can occupy.

        For implementing a lot of constraints it is very helpful to know at which exact Timeslots a
        Lesson takes place at.

        For this purpose this function creates a list for every Lesson with variables for every
        Timeslot. The variables will take the value 1 if the Lesson is held on the Timeslot the
        variable represents and the value 0 if this is not the case.

        Args:
            model(CpModel): The or-tools model for constraint programming optimization.
            orm(ORM):       The object-relation-mapper script that contains lists with
                            all data of the timetable.

        Returns:
            variableCount(int):         The number of created or-tools variables in this function.
            linConstraintCount(int):    The number of added linear constraints to the CpModel.
            otherConstraintCount(int):  The number of all other added constraints to the CpModel.
        """

    # Count created variables and constraints added to the CpModel for debugging and testing
    variableCount = 0
    linConstraintCount = 0
    otherConstraintCount = 0

    falseVar = model.NewIntVar(0, 0, "False")  # This var can only be Zero it is used for Timeslots
    # the Lesson can not occupy.

    for lesson in orm.getLessons():
        timeslotBoolVarsAll = []  # This list will contain a list with boolVars for every timeVar
        #  in the Lessons timeVars list.
        for timeVar in lesson.timeVars:
            timeslotBoolVars = []
            for t in orm.getTimeslots():  # Append a new BoolVar or the falseVar for every Timeslot.
                if t in lesson.availableTimeslotsFiltered:
                    timeslotBoolVars.append(model.NewBoolVar(""))
                    variableCount += 1
                else:  # Add the falseVar if the Lesson can not take place at the Timeslot t because
                    #  it is not in the availableTimeslots list of the Lesson.
                    timeslotBoolVars.append(falseVar)

            model.Add(sum(timeslotBoolVars) == 1)  # Allow exact one variable to be True.
            linConstraintCount += 1
            # The timeVar takes the value of the ID od the Timeslot this part of the Lesson takes
            # place at.(Look at createLessonTimeAndRoomVariables)
            # Every created boolVar is multiplied with the ID of the Timeslot it represents. Because
            # only one of them can be True and the sum of all has to be the value of the timeVar,
            # only the correct boolVar can be True when the Lesson occupies its corresponding Timeslot.
            model.Add(timeVar == sum([t.id * timeslotBoolVars[t.id-1] for t in orm.getTimeslots()]))
            linConstraintCount += 1
            timeslotBoolVarsAll.append(timeslotBoolVars)

        if len(timeslotBoolVarsAll) > 1:
            # Create new list with boolVars to represent the sum of the lists for the single timeVars.
            timeslotBoolVars = []
            for t in orm.getTimeslots():
                if t in lesson.availableTimeslotsFiltered:
                    timeslotBoolVars.append(model.NewBoolVar(""))
                    variableCount += 1
                else:
                    timeslotBoolVars.append(falseVar)

            for i in range(len(orm.getTimeslots())):
                # If it is possible that the Lesson takes place at this Timeslot, make the new boolVar
                # to be True if one of the boolVars of the timeVars of this Timeslot is True.
                if timeslotBoolVars[i] is not falseVar:
                    model.Add(timeslotBoolVars[i] == sum([b[i] for b in timeslotBoolVarsAll]))
                    # timeslotsBoolVars[i] <==> timeslotBoolVarsAll[0][i] OR timeslotBoolVarsAll[1][i] OR timeslotBoolVarsAll[2][i] ...
                    otherConstraintCount += 1

            lesson.timeslotBoolVars = timeslotBoolVars
        else:
            # If there is only one timeVar in the Lessons timeVars list, the in the first step created
            # list is already the boolVar list we need.
            lesson.timeslotBoolVars = timeslotBoolVarsAll[0]

    logger.logVariables("LessonTakePlaceVariables", variableCount, linConstraintCount, otherConstraintCount)
    return variableCount, linConstraintCount, otherConstraintCount


def createTeacherLectureAtTimeslotMap(model: CpModel, orm: ORM):
    """Creates helper variables for the the Lectures a Teacher gives.

        For implementing a the constraints with Lectures a Teacher gives it is very helpful to know
        at which exact Timeslots a Teacher gives a Lecture.

        For this purpose this function creates a dictionary for every Teacher with all Timeslots as
        keys and each a BoolVar as value. The BoolVars are indicating if the Teacher gives a Lecture at
        the corresponding Timeslot.

        Args:
            model(CpModel): The or-tools model for constraint programming optimization.
            orm(ORM):       The object-relation-mapper script that contains lists with
                            all data of the timetable.

        Returns:
            variableCount(int):         The number of created or-tools variables in this function.
            linConstraintCount(int):    The number of added linear constraints to the CpModel.
            otherConstraintCount(int):  The number of all other added constraints to the CpModel.
        """

    # Count created variables and constraints added to the CpModel for debugging and testing
    variableCount = 0
    linConstraintCount = 0
    otherConstraintCount = 0

    for teacher in orm.getTeachers():
        # Dictionary that will contain a boolVar for every Timeslot that indicates if the Teacher
        # gives a Lecture at this Timeslot
        teacher.timeslotLectureBoolMap = {}

        # This map will contain for every Timeslot a list with boolVars for every Lecture that are
        # indicating if the Lecture takes place at this Timeslot.
        timeslotLecturesListTakePlaceMap = {}

        # Add empty lists for every Timeslot
        for timeslot in orm.getTimeslots():
            timeslotLecturesListTakePlaceMap[timeslot] = []

        # Add the boolVars of every Lecture the Teacher helds for every Timeslot to the List
        for timeslot in orm.getTimeslots():
            for lesson in filter(lambda l: l.course.is_lecture, teacher.lessons):
                timeslotLecturesListTakePlaceMap[timeslot].append(lesson.timeslotBoolVars[timeslot.id - 1])

        # Create a boolVar for every Timeslot that indicates if the Teacher helds a Lecture at this
        # Timeslot. For this, the boolVar has to be True if any of the Lectures boolVars for this
        # Timeslot are True. tOccupied <==> lecture1.boolVar or lecture2.boolVar or ...
        for timeslot in orm.getTimeslots():
            tOccupied = model.NewBoolVar("")
            variableCount += 1
            model.AddBoolOr(timeslotLecturesListTakePlaceMap[timeslot]).OnlyEnforceIf(tOccupied)
            model.Add(sum(timeslotLecturesListTakePlaceMap[timeslot]) == 0).OnlyEnforceIf(tOccupied.Not())
            otherConstraintCount += 1
            teacher.timeslotLectureBoolMap[timeslot] = tOccupied

    logger.logVariables("TeacherLectureAtTimeslotMap", variableCount, linConstraintCount, otherConstraintCount)
    return variableCount, linConstraintCount, otherConstraintCount


def addTeacherTimeConstraints(model: CpModel, orm: ORM):
    """Ensures that there is never more than one lesson at a time for a teacher.

        It is assumed that lessons that explicitly take place at the same time share their timeVar
        variables so that these duplicates can be filtered out by the set() function.

        Args:
            model(CpModel): The or-tools model for constraint programming optimization.
            orm(ORM):       The object-relation-mapper script that contains lists with
                            all data of the timetable.

        Returns:
            variableCount(int):         The number of created or-tools variables in this function.
            linConstraintCount(int):    The number of added linear constraints to the CpModel.
            otherConstraintCount(int):  The number of all other added constraints to the CpModel.
        """

    # Count added constraints for debugging and testing.
    otherConstraintsCount = 0

    for teacher in orm.getTeachers():
        # The Timeslots of all Lessons the Teacher gives, shall be different.
        model.AddAllDifferent(set(flatMap(lambda l: l.timeVars, teacher.lessons)))
        otherConstraintsCount += 1

    logger.logVariables("TeacherTimeConstraints", 0, 0, otherConstraintsCount)
    return 0, 0, otherConstraintsCount


def addSemesterGroupTimeConstraints(model: CpModel, orm: ORM):
    """Ensures that there is never more than one lesson at a time for a SemesterGroup.

        It is assumed that lessons that explicitly take place at the same time share their timeVar
        variables so that these duplicates can be filtered out by the set() function.

        The other big exception are Lessons with the whole_semester_group flag is False.
        These Lessons can take place at the same Timeslot. To ensure that every student can
        participate at all Lessons he has to, only one Lesson per Course can take place at the same
        Timeslot if there take place Lessons from different Courses at the same Timeslot.

        Args:
            model(CpModel): The or-tools model for constraint programming optimization.
            orm(ORM):       The object-relation-mapper script that contains lists with
                            all data of the timetable.

        Returns:
            variableCount(int):         The number of created or-tools variables in this function.
            linConstraintCount(int):    The number of added linear constraints to the CpModel.
            otherConstraintCount(int):  The number of all other added constraints to the CpModel.
        """

    # Count added constraints and variables for debugging and testing.
    otherConstraintsCount = 0
    variableCount = 0
    linConstraintCount = 0

    for semesterGroup in orm.getSemesterGroups():
        # Create a list with all Lessons the whole SemesterGroup participates at.
        lessonsWithWholeSG = [l for l in semesterGroup.getLessons() if l.whole_semester_group]
        # All different constraint for the Lesson's timeVars to ensure the Lessons take place at
        # different Timeslots .
        model.AddAllDifferent(set(flatMap(lambda l: l.timeVars, lessonsWithWholeSG)))
        otherConstraintsCount += 1

        # Create list with all Lessons only a part of the SemesterGroup participates at.
        lessonsWithPartSG = list(filter(lambda l: not l.whole_semester_group, semesterGroup.getLessons()))
        # None of these Lessons can take place at the same time as one of the Lessons with the whole
        # SemesterGroup.
        for lesson in lessonsWithPartSG:
            model.AddAllDifferent(set(flatMap(lambda l: l.timeVars, lessonsWithWholeSG + [lesson])))
            otherConstraintsCount += 1

        multiBlockLessons = list(filter(lambda l: l.timeslot_size > 1, lessonsWithPartSG))

        # Make sure that either all simultaneous lessons of a semester group are from the same
        # course, or a maximum of one lesson from each course take place at the same time.
        # This is to ensure that all students can always participate in all courses.
        # Also in the following example students can not participate at their lessons.
        # Each Lesson of B consist of 2 Timeslots and the Lessons of course A are of size 1.
        # One half of the semester group could not participate on any Lesson of Course A
        #  Day1   | Day2
        # A1 [B1] | [B2]
        # A2 [B1] | [B2]
        # Because of that prohibit parallel Lessons of different courses if one ore more Lesson
        # has a bigger timeslot_size than 1.

        for timeslot in orm.getTimeslots():
            # List with courses with Lessons with not the whole SemesterGroup of this SemesterGroup
            parallelCourses = list(set(map(lambda l: l.course, lessonsWithPartSG)))
            # BoolVar for every Course. It indicates if the course take place at this Timeslot
            courseTakePlace = list(map(lambda c: model.NewBoolVar(""), parallelCourses))
            variableCount += len(courseTakePlace)

            for i in range(len(parallelCourses)):
                # List with the takePlaceBoolVar for this Timeslot of all Lessons with only part
                # SemesterGroup of the current Course.
                coursesPartSGLessonsBoolVars = [l.timeslotBoolVars[timeslot.id - 1] for l in
                                                parallelCourses[i].lessons if not l.whole_semester_group]
                # courseTakePlace BoolVar will take the value 1 if one of the courses lessons, with
                # not the whole SemesterGroup to participate, takes place at this Timeslot.
                # If one or more of the timeslotBoolVars are true, the maximum is one
                model.AddMaxEquality(courseTakePlace[i], coursesPartSGLessonsBoolVars)
                otherConstraintsCount += 1

            # This BoolVar will be unbound but is used to make one of two constraints always be True
            boolV = model.NewBoolVar("")
            variableCount += 1
            # Case 1:
            # Case for Lessons of only one Course.
            model.Add(sum(courseTakePlace) <= 1).OnlyEnforceIf(boolV)
            # Case 2:
            # Case for parallel Lessons of more than one Course. Then only one Lesson per Course.
            model.Add(sum([l.timeslotBoolVars[timeslot.id - 1] for l in lessonsWithPartSG]) ==
                      sum(courseTakePlace)).OnlyEnforceIf(boolV.Not())
            # And make sure that there is no Lesson with bigger timeslot_size than one.
            model.Add(sum([l.timeslotBoolVars[timeslot.id - 1] for l in multiBlockLessons]) ==
                      0).OnlyEnforceIf(boolV.Not())
            linConstraintCount += 3

    logger.logVariables("SemesterGroupTimeConstraints", variableCount, linConstraintCount, otherConstraintsCount)
    return variableCount, linConstraintCount, otherConstraintsCount


def addRoomTimeConstraints(model: CpModel, orm: ORM):
    """Adds constraints to the CpModel to ensure that no several Lessons can ever take place in the
    same room on same time.

        Since it is not given where and when most Lessons will take place, securing this Constraint
        is somewhat more complex. For all pairs of Lessons that can take place in the same Rooms, a
        boolean variable is created to indicate whether the lessons actually take place in the same
        Room. Then constraints are added that prevent the lessons from taking place at the same time
        when the boolean room variable is True. This happens in three different ways, depending on
        whether both lessons are several Timeslots long, both are one Timeslot long, or are mixed.

        Args:
            model(CpModel): The or-tools model for constraint programming optimization.
            orm(ORM):       The object-relation-mapper script that contains lists with
                            all data of the timetable.

        Returns:
            variableCount(int):         The number of created or-tools variables in this function.
            linConstraintCount(int):    The number of added linear constraints to the CpModel.
            otherConstraintCount(int):  The number of all other added constraints to the CpModel.
        """

    # Count added constraints and variables for debugging and testing.
    linConstraintsCount = 0
    otherConstraintsCount = 0
    variableCount = 0

    # Function for creating IntervalVars for Lessons with a size bigger than one.
    def createLessonIntervalVar(lesson: Lesson, model):
        # The intervals should start with one less than the ID of the Timeslot the Lesson starts at
        # and end with the Timeslots ID the Lessons end.
        # The start at the ID -1 is because NoOverlap Constraints allows same number on
        # start or end of two intervals. Due to this make the interval one bigger,
        # to exclude this overlaps.
        # (NoOverlap assumes that the numbers are (infinite small) timepoints)
        dummyVar = model.NewIntVar(0, len(orm.getTimeslots()), "")
        model.Add(dummyVar == lesson.timeVars[0] - 1)  # Lesson start - 1
        lesson.timeInterval = model.NewIntervalVar(
            dummyVar,  # Lessons start - 1
            lesson.timeslot_size,  # Size of the interval
            lesson.timeVars[lesson.timeslot_size - 1], "")  # Lessons end

    # Iterate over all pairs of two Lessons.
    for i in range(len(orm.getLessons())):
        for j in range(i + 1, len(orm.getLessons())):
            lesson_i, lesson_j = orm.getLessons()[i], orm.getLessons()[j]
            room_intersection = list(set(lesson_i.course.possible_rooms) & set(lesson_j.course.possible_rooms))

            # Its only needed to add constraints if the two Lessons can actually take place in the same room.
            # Also, Lessons with the SameTimeConstraint should be able to take place in the same Room to the same time.
            if len(room_intersection) > 0 and lesson_j not in lesson_i.lessons_at_same_time:
                # Create BoolVar that indicates if the Lessons take place in the same Room.
                sameRoom = model.NewBoolVar("")
                model.Add(orm.getLessons()[i].roomVar == orm.getLessons()[j].roomVar).OnlyEnforceIf(sameRoom)
                model.Add(orm.getLessons()[i].roomVar != orm.getLessons()[j].roomVar).OnlyEnforceIf(sameRoom.Not())
                variableCount += 1
                linConstraintsCount += 2

                #  Possible room_time conflicts between Lessons with multi Timeslots each:
                if lesson_i.timeslot_size > 1 and lesson_j.timeslot_size > 1:
                    # If not already done, create IntervalVars for both Lessons.
                    if not hasattr(lesson_i, "timeInterval"):
                        createLessonIntervalVar(lesson_i, model)
                        variableCount += 2
                        linConstraintsCount += 1
                    if not hasattr(lesson_j, "timeInterval"):
                        createLessonIntervalVar(lesson_j, model)
                        variableCount += 2
                        linConstraintsCount += 1

                    # Enforce that the Lessons doesnt overlap in time if the Lessons take place in
                    # the same Room.
                    model.AddNoOverlap([lesson_i.timeInterval, lesson_j.timeInterval]).OnlyEnforceIf(sameRoom)
                    variableCount += 2
                    linConstraintsCount += 1

                # One or none of the Lessons has a timeslot_size > 1:
                else:
                    # Maximal one of the for loops is run through more than once, because at least
                    # one of the timeslot_size vars is == 1. This way you don't have to test which
                    # Lesson's may have a timeslot_size > 1.
                    for k in range(lesson_i.timeslot_size):
                        for l in range(lesson_j.timeslot_size):
                            # Make sure all Timeslots the Lessons occupy are different.
                            model.Add(lesson_i.timeVars[k] != lesson_j.timeVars[l]) \
                                .OnlyEnforceIf(sameRoom)
                            linConstraintsCount += 1

    logger.logVariables("RoomTimeConstraints:", variableCount, linConstraintsCount, otherConstraintsCount)
    return variableCount, linConstraintsCount, otherConstraintsCount


def addTeacherStudyDayConstraints(model: CpModel, orm: ORM):
    """Adds constraints to the CpModel to ensure that every Teacher with a studyday has at least
        on one of the Teachers choices a free weekday without any Lessons.

        Each Teacher has two choices for his study day. It is ensured that on (at least) one of them
        no Lessons the Teacher gives take place. The two choices can be the same day. In this case
        it is ensured that there are no Lessons on this specific day. Of course, of the choice
        interferes with other constraints like the TakePlaceAt constraint, the model will be infeasible.

        Args:
            model(CpModel): The or-tools model for constraint programming optimization.
            orm(ORM):       The object-relation-mapper script that contains lists with
                            all data of the timetable.

        Returns:
            variableCount(int):         The number of created or-tools variables in this function.
            linConstraintCount(int):    The number of added linear constraints to the CpModel.
            otherConstraintCount(int):  The number of all other added constraints to the CpModel.
        """

    # Count added constraints and variables for debugging and testing.
    variableCount = 0
    linConstraintCount = 0
    otherConstraintCount = 0

    # Add constraints for all Teacher objects that has a studyday.
    for teacher in filter(lambda t: t.hasStudyday(), orm.getTeachers()):
        # Retrieve the ID of the two weekdays.
        studyDay1ID = Timeslot.getWeekdayID(teacher.study_day_1)
        studyDay2ID = Timeslot.getWeekdayID(teacher.study_day_2)

        if len(teacher.lessons) > 0:  # No action required if the Teacher has no Lessons ;-)
            # Create a BoolVar for the two choices. The BoolVar should be True if there are no
            # Lessons at the weekday it represents.
            teacher.studyDay1BoolVar = model.NewBoolVar("")
            # Reuse the first variable if the two choices are the same day.
            teacher.studyDay2BoolVar = model.NewBoolVar("") if \
                studyDay1ID != studyDay2ID else teacher.studyDay1BoolVar

            # Length of a set of the study days. Will be one if the days are the same.
            variableCount += len({teacher.studyDay1BoolVar, teacher.studyDay2BoolVar})

            # Ensure all Lessons weekdayVar to be different from the studyday whose BoolVar is True.
            for lesson in teacher.lessons:
                model.Add(studyDay1ID != lesson.weekdayVar).OnlyEnforceIf(teacher.studyDay1BoolVar)
                linConstraintCount += 1

                if studyDay1ID != studyDay2ID:  # Only necessary if the choices are not equal.
                    model.Add(studyDay2ID != lesson.weekdayVar).OnlyEnforceIf(teacher.studyDay2BoolVar)
                    linConstraintCount += 1

            # At least one of the studyday BoolVars has to be True.
            model.AddBoolOr([teacher.studyDay1BoolVar, teacher.studyDay2BoolVar])
            otherConstraintCount += 1

    logger.logVariables("TeacherStudyDayConstraints:", variableCount, linConstraintCount, otherConstraintCount)
    return variableCount, linConstraintCount, otherConstraintCount


def addRoomNotAvailableConstraints(model: CpModel, orm: ORM):
    """Adds constraints to the CpModel to ensure that Rooms cannot be occupied on Timeslots that
    are prohibited through the RoomNotAvailable Constraint.

    If RoomNotAvailable times interfere with AvailableLessonTimeConstraint Timeslots, the model will be
    infeasible.

        Args:
            model(CpModel): The or-tools model for constraint programming optimization.
            orm(ORM):       The object-relation-mapper script that contains lists with
                            all data of the timetable.

        Returns:
            variableCount(int):         The number of created or-tools variables in this function.
            linConstraintCount(int):    The number of added linear constraints to the CpModel.
            otherConstraintCount(int):  The number of all other added constraints to the CpModel.
        """

    # Count added constraints and variables for debugging and testing.
    linConstraintCount = 0
    variableCount = 0

    for room in orm.getRooms():
        # An empty list means the room is available at all Timeslots.
        if len(room.not_available_timeslots) > 0:
            # Iterate over Lessons that can take place in the Room.
            for lesson in filter(lambda l: room in l.course.possible_rooms, orm.getLessons()):
                # Create a BoolVar that indicates if the Lesson takes place in the Room.
                inRoom = model.NewBoolVar("")
                model.Add(lesson.roomVar == room.id).OnlyEnforceIf(inRoom)
                model.Add(lesson.roomVar != room.id).OnlyEnforceIf(inRoom.Not())
                variableCount += 1
                linConstraintCount += 2

                # Ensure for all Timeslots of the Lesson and not_available_timeslots of the Room
                # not to be equal if the Lesson takes place in the Room.
                for timeslot in room.not_available_timeslots:
                    for timeVar in lesson.timeVars:
                        model.Add(timeVar != timeslot.id).OnlyEnforceIf(inRoom)
                        linConstraintCount += 1

    logger.logVariables("RoomNotAvailableConstraints:", variableCount, linConstraintCount, 0)
    return variableCount, linConstraintCount, 0


def addCourseAllInOneBlockConstraints(model: CpModel, orm):
    """Adds constraints to the CpModel to ensure that all Lessons of Courses with the
    all_in_one_block flag set take place as block on a single day.

    The model will be infeasible if the Course Contains Lessons with summed timeslot_size greater
    than the Timeslot count of a day or the max Lessons for the teaching Teacher or the SemesterGroup.

        Args:
            model(CpModel): The or-tools model for constraint programming optimization.
            orm(ORM):       The object-relation-mapper script that contains lists with
                            all data of the timetable.

        Returns:
            variableCount(int):         The number of created or-tools variables in this function.
            linConstraintCount(int):    The number of added linear constraints to the CpModel.
            otherConstraintCount(int):  The number of all other added constraints to the CpModel.
        """

    # Count added constraints and variables for debugging and testing.
    variableCount = 0
    linConstraintCount = 0
    otherConstraintCount = 0

    for course in filter(lambda c: c.all_in_one_block, orm.getCourses()):
        blocksize = sum(map(lambda l: l.timeslot_size, course.lessons))
        if blocksize > 1:
            # The last possible Timeslot number of the day the block can start.
            lastStartPossible = TIMESLOTS_PER_DAY + 1 - blocksize

            # Variables for the total start and end of the block. minVar will be equal to the first
            # timeVar of the first Lesson in the block and maxVar will be equl to the last timeVar
            # of the last Lesson in the block.
            minVar = model.NewIntVar(1, len(orm.getTimeslots()), "")
            maxVar = model.NewIntVar(1, len(orm.getTimeslots()), "")
            # Assign the start and end values.
            model.AddMinEquality(minVar, course.getAllTimeVars())
            model.AddMaxEquality(maxVar, course.getAllTimeVars())
            # Add IntervalVar, this already ensures the Lessons take place directly subsequent.
            # (Even there are more than two Lessons, because of the Min and Max Equality Constraints)
            model.NewIntervalVar(minVar, blocksize - 1, maxVar, "")
            # The Interval constraint is valid once the interval variable has been created.
            # It does not need to be saved separately.
            variableCount += 3
            otherConstraintCount += 2

            # Now ensure that the whole block take place within one single day.
            # Create a variable that indicates the hour number the block starts.
            # The values is e.g. 1 for the first Timeslot of a day. It cannot take the number for
            # the last Timeslot of a day because the blocksize has to be at least 2.
            minHourNumberVar = model.NewIntVar(1, lastStartPossible, "")
            # minHourNumberVar == minVar modulo TIMESLOTS_PER_DAY
            # The first hour of the block cannot be the last Timeslot of the day, so it doesn't
            # matter the value of the minHourNumberVar would be zero for the last hour.
            model.AddModuloEquality(minHourNumberVar, minVar, TIMESLOTS_PER_DAY)
            # Ensure the firstHourNumberVar is between 1 and the last possible start
            # ( TIMESLOTS_PER_DAY + 1 - blocksize )
            # It is assumed that the blocksize is always > 1 and can never start on the last hour
            # of the day.
            variableCount += 1
            otherConstraintCount += 1

            # All lessons in a block should take place in the same room.
            for i in range(1, len(course.lessons)):
                model.Add(course.lessons[i - 1].roomVar == course.lessons[i].roomVar)
                linConstraintCount += 1

    logger.logVariables("CourseAllInOneBlockConstraints:", variableCount, linConstraintCount, otherConstraintCount)
    return variableCount, linConstraintCount, otherConstraintCount


def addConsecutiveLessonsConstraints(model: CpModel, orm):
    """Adds constraints to the CpModel to ensure that all the ConsecutiveLessonsConstraints are
    fulfilled and all Lessons as stated take place directly after another.

    All lessons in the lessons_consecutive list of a lesson should take place directly after the
    lesson.

        Args:
            model(CpModel): The or-tools model for constraint programming optimization.
            orm(ORM):       The object-relation-mapper script that contains lists with
                            all data of the timetable.

        Returns:
            variableCount(int):         The number of created or-tools variables in this function.
            linConstraintCount(int):    The number of added linear constraints to the CpModel.
            otherConstraintCount(int):  The number of all other added constraints to the CpModel.
        """

    # Count added constraints and variables for debugging and testing.
    linConstraintCount = 0

    for lesson in orm.getLessons():
        for consecutiveLesson in lesson.lessons_consecutive:
            # Ensure the Lessons take place on the same day.
            model.Add(lesson.weekdayVar == consecutiveLesson.weekdayVar)
            # Ensure that the Lessons of the lessons_consecutive list start at the Timeslot after
            # the last Timeslot of the origin Lesson.
            model.Add(lesson.timeVars[-1] + 1 == consecutiveLesson.timeVars[0])
            linConstraintCount += 2

    logger.logVariables("ConsecutiveLessonsConstraints:", 0, linConstraintCount, 0)
    return 0, linConstraintCount, 0


def addMaxLessonsPerDayTeacherConstraints(model: CpModel, orm):
    """Adds constraints to the CpModel to ensure that all Teachers have at most as many
    Lesson Timeslots per day as specified for them.

    Args:
        model(CpModel): The or-tools model for constraint programming optimization.
        orm(ORM):       The object-relation-mapper script that contains lists with
                        all data of the timetable.

    Returns:
        variableCount(int):         The number of created or-tools variables in this function.
        linConstraintCount(int):    The number of added linear constraints to the CpModel.
        otherConstraintCount(int):  The number of all other added constraints to the CpModel.
    """

    # Count added constraints and variables for debugging and testing.
    linConstraintCount = 0

    for teacher in orm.getTeachers():
        # Create set with lessons with the teacher, but only the longest lesson of lessons in a
        # lessons_at_same_time constraint.
        # First add lessons without lessons_at_same_time constraint.
        lessonsForTeacher = set([x for x in teacher.lessons if not x.lessons_at_same_time])

        # Iterate over sets of Lessons that take place at the same time by the LessonsAtSameTime
        # constraint.
        for sameTimeSet in orm.getLessonsAtSameTimeSets():
            # Get Lessons with teacher:
            sameTimeLessons = [x for x in sameTimeSet if x in teacher.lessons]
            if sameTimeLessons:  # Only if list not empty and only add longest Lesson.
                lessonsForTeacher.add(max(sameTimeLessons, key=lambda l: l.timeslot_size))

        # Make sum of Timeslots on each weekday. Constraint makes this sum <= max Timeslots per day.
        for day in range(orm.WEEKDAYS):  # The Teachers Lessons of each weekday. day is an int [0,WEEKDAYS)
            model.Add(  # Summarize the Lesson's sizes from the generated set.
                sum(list(map(lambda l: l.timeslot_size * l.weekdayBoolVars[day], lessonsForTeacher)))
                <= teacher.max_lessons_per_day
            )
            linConstraintCount += 1

        # ### ONLY FOR DEBUGGING ###
        # For debugging add sumVars list:
        # teacher.sumTimeslotsPerDay = []
        # for weekdayIndex in range(0, len(orm.getTimeslotsPerDay())):  # iterate for each weekday
        #     sumVar = model.NewIntVar(0, teacher.max_lessons_per_day, "")
        #     teacher.sumTimeslotsPerDay.append(sumVar)
        #     model.Add(sum(list(map(lambda l: l.timeslot_size * l.weekdayBoolVars[weekdayIndex], lessonsForTeacher))) == sumVar)

    logger.logVariables("MaxLessonsPerDayTeacherConstraints:", 0, linConstraintCount, 0)
    return 0, linConstraintCount, 0


def addMaxLessonsPerDaySemesterGroupConstraints(model: CpModel, orm):
    """Adds constraints to the CpModel to ensure that all SemesterGroups have
    at most as many Lesson Timeslots per day as specified for them.

    Args:
        model(CpModel): The or-tools model for constraint programming optimization.
        orm(ORM):       The object-relation-mapper script that contains lists with
                        all data of the timetable.

    Returns:
        variableCount(int):         The number of created or-tools variables in this function.
        linConstraintCount(int):    The number of added linear constraints to the CpModel.
        otherConstraintCount(int):  The number of all other added constraints to the CpModel.
    """

    """
    In some cases there may be inaccuracies in counting hours from a student's point of view:
    -If from a partSemesterGroup Course some but not all lessons are part of a lessons_at_same_time
    constraint, two Timeslots are counted if the single lessons and the same_time group take place
    on the same day.
    -In the second case, a same_time_constraint in which both a lesson with an entire SemesterGroup
    and a lesson with a PartSemesterGroup are included counts the two lessons as two Timeslots even
    though they are listed at the same time.
    -Lessons with partSG of different courses that take place at the same timeslot may be counted both.
    """

    # Count added constraints and variables for debugging and testing.
    linConstraintCount = 0
    variableCount = 0
    otherConstaintCount = 0

    # Do for all SemesterGroups.
    for semesterGroup in orm.getSemesterGroups():
        # Create set with lessons the whole SemesterGroup participates at.
        # If a Lesson is in an SameTimeConstraint, pick only the longest.
        lessonsWithWholeSG = set()
        # First, add lessons with whole SemesterGroup and not in a LessonsAtSameTimeConstraint.
        for l in semesterGroup.getLessons():
            if l.whole_semester_group and not l.lessons_at_same_time:
                lessonsWithWholeSG.add(l)

        # Second, add longest Lessons in a LessonsAtSameTimeConstraint,
        # but only if this Lesson is with the whole SemesterGroup. Either way, ignore the others
        # in the constraint, even if one of them is with whole SemesterGroup. This is because the
        # longest Lesson of the constraint will be picked in the next step, if it is not with the
        # whole SemesterGroup.
        for sameTimeSet in orm.getLessonsAtSameTimeSets():
            sameTimeLessons = [x for x in sameTimeSet if x in semesterGroup.getLessons()]
            # Pick longest lesson, but take the wholeSemesterGroup boolean as second key.
            # This is to ensure the picked Lesson is only a wholeSemesterGroup lesson, if there is
            # no other lesson with the same size and that is a partGroupLesson. As partGroupLesson,
            # that lesson will be counted in the next step.
            if sameTimeLessons:
                longestLesson = max(sameTimeLessons, key=lambda l: (l.timeslot_size, not l.whole_semester_group))
                # Only add a lesson at all, if the longest lesson is with the whole SemesterGroup,
                # because if this is not the case, the lesson will be counted in the next step anyway.
                if longestLesson.whole_semester_group:
                    lessonsWithWholeSG.add(longestLesson)

        # ### ONLY FOR DEBUGGING ###
        # semesterGroup.sumTimeslotsPerDay = []  # save sum as vars for testing

        for weekdayIndex in range(orm.WEEKDAYS):  # iterate for each weekday
            # List with variables for timeslot_size and take_place_var for each course that
            # has lessons with whole_semester_group == False.
            partSGCourses = []
            for course in semesterGroup.courses:
                partSemesterGroupLessons = [x for x in course.lessons if not x.whole_semester_group]
                if partSemesterGroupLessons:
                    lessonSize = partSemesterGroupLessons[0].timeslot_size  # assume that all lessons of this course on that only a part of the SemesterGroup participates have the same length
                    courseTakePlaceVar = model.NewBoolVar("")
                    model.AddMaxEquality(courseTakePlaceVar, [l.weekdayBoolVars[weekdayIndex] for l in partSemesterGroupLessons])
                    partSGCourses.append((courseTakePlaceVar, lessonSize))

                    variableCount += 1  # Count for debugging.
                    otherConstaintCount += 1

            model.Add(
                sum(map(lambda l: l.timeslot_size * l.weekdayBoolVars[weekdayIndex], lessonsWithWholeSG)) +
                sum(map(lambda c: c[0] * c[1], partSGCourses))
                <= semesterGroup.max_lessons_per_day)  # lessons for weekdayIndex
            linConstraintCount += 1

            # ### ONLY FOR DEBUGGING ###
            # save sum as var for testing
            # sumVar = model.NewIntVar(0, semesterGroup.max_lessons_per_day, "")
            # semesterGroup.sumTimeslotsPerDay.append(sumVar)
            # model.Add(
            #     sum(map(lambda l: l.weekdayBoolVars[weekdayIndex] * l.timeslot_size, lessonsWithWholeSG)) +
            #     sum(map(lambda c: c[0] * c[1], partSGCourses))
            #     == sumVar)

    logger.logVariables("MaxLessonsPerDaySemesterGroupConstraints",
                        variableCount, linConstraintCount, otherConstaintCount)
    return variableCount, linConstraintCount, otherConstaintCount


def addMaxLessonsPerDayCourseConstraints(model: CpModel, orm):
    """Adds constraints to the CpModel to ensure there is at most one lesson per course and day.

    Lessons with parts of semester groups,
    lessons in a LessonsAtSameTime constraint and
    lessons of AllInOneBlock courses are excluded.

    Args:
        model(CpModel): The or-tools model for constraint programming optimization.
        orm(ORM):       The object-relation-mapper script that contains lists with
                        all data of the timetable.

    Returns:
        variableCount(int):         The number of created or-tools variables in this function.
        linConstraintCount(int):    The number of added linear constraints to the CpModel.
        otherConstraintCount(int):  The number of all other added constraints to the CpModel.
    """

    # Count added constraints and variables for debugging and testing.
    linConstraintCount = 0

    # Exclude AllInOneBlock courses.
    for course in filter(lambda c: not c.all_in_one_block, orm.getCourses()):
        for weekdayIndex in range(orm.WEEKDAYS):  # Iterate for each weekday.
            # Filter for lessons with whole semester groups
            # and not in a LessonsAtSameTime constraint.
            relevantLessons = list(filter(lambda l: l.whole_semester_group
                                                    and not l.lessons_at_same_time, course.lessons))
            if relevantLessons:
                # Only one of the relevant lessons per day.
                model.Add(sum([l.weekdayBoolVars[weekdayIndex] for l in relevantLessons]) <= 1)
                linConstraintCount += 1

    logger.logVariables("MaxLessonsPerDayCourseConstraints", 0, linConstraintCount, 0)
    return 0, linConstraintCount, 0


# ! Call addMaxLecturesAsBlockTeacherConstraints after(!) this function to make it work properly !
def addMaxLecturesAsBlockTeacherConstraints(model: CpModel, orm):
    """Adds constraints to the CpModel to ensure no, with lecture-lessons occupied, timeslots
    with bigger blocksize than given for each teacher, can occur.

    This function reduces the variables max_lectures_per_day and max_lectures_as_bock for
    each teacher object to sinful values. To fulfill the MaxLecturesAsBlock constraint correctly,
    it is needed to call the function addMaxLecturesPerDayTeacherConstraints afterwards!

    Args:
        model(CpModel): The or-tools model for constraint programming optimization.
        orm(ORM):       The object-relation-mapper script that contains lists with
                        all data of the timetable.

    Returns:
        variableCount(int):         The number of created or-tools variables in this function.
        linConstraintCount(int):    The number of added linear constraints to the CpModel.
        otherConstraintCount(int):  The number of all other added constraints to the CpModel.
    """

    # Count added constraints and variables for debugging and testing.
    otherConstraintCount = 0

    # Enumerate all forbidden assignments for all relevant
    # combinations of maxLecturesPerDay and maxLectureAsBlock.

    # enumerate all blocks of size 5
    max5_maxblock_4 = [[1, 1, 1, 1, 1, 0], [0, 1, 1, 1, 1, 1]]
    # List for maxLecturesPerDay = 5 and maxLectureBlock = 4.
    # (It is deviated from camelcase in order to be able to read
    # these values in the variable names better.)

    # enumerate all blocks of size 4
    max4_maxblock_3 = [[1, 1, 1, 1, 0, 0], [0, 1, 1, 1, 1, 0], [0, 0, 1, 1, 1, 1]]
    max5_maxblock_3 = [[1, 1, 1, 1, 0, 1], [1, 0, 1, 1, 1, 1]] + max4_maxblock_3 + max5_maxblock_4

    # enumerate all blocks of size 3
    max3_maxblock_2 = [[1, 1, 1, 0, 0, 0], [0, 1, 1, 1, 0, 0], [0, 0, 1, 1, 1, 0], [0, 0, 0, 1, 1, 1]]
    max4_maxblock_2 = [[1, 1, 1, 0, 1, 0], [1, 1, 1, 0, 0, 1], [0, 1, 1, 1, 0, 1], [1, 0, 1, 1, 1, 0], [0, 1, 0, 1, 1, 1], [1, 0, 0, 1, 1, 1], [1, 0, 0, 1, 1, 1]] + max3_maxblock_2 + max4_maxblock_3

    # enumerate all blocks of size 2
    max2_maxblock_1 = [[1, 1, 0, 0, 0, 0], [0, 1, 1, 0, 0, 0], [0, 0, 1, 1, 0, 0], [0, 0, 0, 1, 1, 0], [0, 0, 0, 0, 1, 1]]
    max3_maxblock_1 = [[1, 1, 0, 1, 0, 0], [1, 1, 0, 0, 1, 0], [1, 1, 0, 0, 0, 1], [0, 1, 1, 0, 1, 0], [0, 1, 1, 0, 0, 1], [1, 0, 1, 1, 0, 0], [0, 0, 1, 1, 0, 1], [0, 1, 0, 1, 1, 0], [1, 0, 0, 1, 1, 0], [0, 0, 1, 0, 1, 1], [0, 1, 0, 0, 1, 1], [1, 0, 0, 0, 1, 1]] + max2_maxblock_1 + max3_maxblock_2

    for teacher in orm.getTeachers():
        # Reduce maxLecturesPerDay and maxLecturesAsBlock to sinfully values
        # and select the forbidden constellations of occupied timeslots.

        forbidden_assignments = []

        # Reduce maxBlocksize to maxLecturesPerDay if bigger.
        if teacher.max_lectures_as_block > teacher.max_lectures_per_day:
            teacher.max_lectures_as_block = teacher.max_lectures_per_day

        # Reduce maxLecturesPerDay if with given maxBlocksize
        # not as much occupied timeslots per day possible.
        # Also select the forbidden assignments.
        if teacher.max_lectures_per_day == 6:
            if teacher.max_lectures_as_block != 6:
                teacher.max_lectures_per_day = 5

        if teacher.max_lectures_per_day == 5:
            if teacher.max_lectures_as_block == 4:
                forbidden_assignments = max5_maxblock_4
            elif teacher.max_lectures_as_block == 3:
                forbidden_assignments = max5_maxblock_3
            elif teacher.max_lectures_as_block < 3:
                teacher.max_lectures_per_day = 4

        if teacher.max_lectures_per_day == 4:
            if teacher.max_lectures_as_block == 3:
                forbidden_assignments = max4_maxblock_3
            elif teacher.max_lectures_as_block == 2:
                forbidden_assignments = max4_maxblock_2
            elif teacher.max_lectures_as_block < 2:
                teacher.max_lectures_per_day = 3

        if teacher.max_lectures_per_day == 3:
            if teacher.max_lectures_as_block == 2:
                forbidden_assignments = max3_maxblock_2
            elif teacher.max_lectures_as_block == 1:
                forbidden_assignments = max3_maxblock_1

        if teacher.max_lectures_per_day == 2:
            if teacher.max_lectures_as_block == 1:
                forbidden_assignments = max2_maxblock_1

        if forbidden_assignments:  # Skip empty list. No Constraint necessary.
            for day in orm.getTimeslotsPerDay():
                boolVarList = list(map(lambda t: teacher.timeslotLectureBoolMap[t], day))
                model.AddForbiddenAssignments(boolVarList, tuple(forbidden_assignments))
                otherConstraintCount += 1

    logger.logVariables("MaxLecturesAsBlockTeacherConstraints:", 0, 0, otherConstraintCount)
    return 0, 0, otherConstraintCount


def addMaxLecturesPerDayTeacherConstraints(model: CpModel, orm):
    """Adds constraints to the CpModel to ensure no, each teacher has at max the number of
    timeslots with lecture-lessons per day as given.

    If more than one lecture-lesson is in the same LessonsAtSameTime constraint, only the
    longest of them will be counted to the number of lecture-lesson-timeslots of that day.

    Args:
        model(CpModel): The or-tools model for constraint programming optimization.
        orm(ORM):       The object-relation-mapper script that contains lists with
                        all data of the timetable.

    Returns:
        variableCount(int):         The number of created or-tools variables in this function.
        linConstraintCount(int):    The number of added linear constraints to the CpModel.
        otherConstraintCount(int):  The number of all other added constraints to the CpModel.
    """

    # Count added constraints and variables for debugging and testing.
    linConstraintCount = 0

    for teacher in orm.getTeachers():
        # Create set with lectures with the teacher.
        # But for LessonsAtSameTime constraints, add only the longest of the containing lectures.
        lecturesForTeacher = set()

        # Add lectures without lessons_at_same_time constraint.
        nonSameTimeLectures = [x for x in teacher.lessons if x.course.is_lecture and not x.lessons_at_same_time]
        lecturesForTeacher.update(nonSameTimeLectures)

        # Add lectures in LessonsAtSameTime constraints.
        # The ORM function returns a list of sets. Each set is containing all
        # same-time-lessons of a LessonsAtSameTime constraint.
        for sameTimeSet in orm.getLessonsAtSameTimeSets():
            # Filter for lessons with the teacher and lectures.
            lectures = [l for l in sameTimeSet if l in teacher.lessons and l.course.is_lecture]
            if lectures:  # Only if list not empty, append longest lesson.
                lecturesForTeacher.add(max(lectures, key=lambda l: l.timeslot_size))

        # ### ONLY FOR DEBUGGING ###
        # for debugging add sumVars
        # teacher.sumLectureTimeslotsPerDay = []
        # for weekdayIndex in range(0, len(orm.getTimeslotsPerDay())):  # iterate for each weekday
        #     sumVar = model.NewIntVar(0, teacher.max_lessons_per_day, "")
        #     teacher.sumLectureTimeslotsPerDay.append(sumVar)
        #     model.Add(sum(list(map(lambda l: l.timeslot_size * l.weekdayBoolVars[weekdayIndex], lecturesForTeacher))) == sumVar)

        # Limit the number of timeslots occupied with the created lessons set per day.
        for dayIndex in range(orm.WEEKDAYS):
            # weekdayBoolVars contains the information if the lesson l takes place at the
            # weekday. Multiply that boolean [1,0] with the lessons size to count the number
            # of occupied timeslots on that day.
            lessonOccurrenceList = [l.timeslot_size * l.weekdayBoolVars[dayIndex] for l in lecturesForTeacher]
            model.Add(sum(lessonOccurrenceList) <= teacher.max_lectures_per_day)
            linConstraintCount += 1

    logger.logVariables("MaxLecturesPerDayTeacherConstraints", 0, linConstraintCount, 0)
    return 0, linConstraintCount, 0


def addOneCoursePerDayPerTeacherConstraints(model: CpModel, orm):
    """Adds constraints to the CpModel to ensure only lessons of one OneCoursePerDay-course
    take place on the same day for a teacher. Does not effect any non OneCoursePerDay courses.

    Args:
        model(CpModel): The or-tools model for constraint programming optimization.
        orm(ORM):       The object-relation-mapper script that contains lists with
                        all data of the timetable.

    Returns:
        variableCount(int):         The number of created or-tools variables in this function.
        linConstraintCount(int):    The number of added linear constraints to the CpModel.
        otherConstraintCount(int):  The number of all other added constraints to the CpModel.
    """

    # Count added constraints and variables for debugging and testing.
    linConstraintCount = 0

    # Do for all Teacher objects.
    for teacher in orm.getTeachers():
        # Collect the OneCoursePerDay courses of the teacher.
        one_per_day_courses = list(filter(lambda c: c.one_per_day_per_teacher, teacher.getCourses()))

        # Enumerate all 2-combinations of courses of the courseList. (All two elementary subsets)
        # Use the two indexes i and j to pick a 2-combination of courses.
        for i in range(len(one_per_day_courses)):
            for j in range(i + 1, len(one_per_day_courses)):
                # Enumerate all elements in the cartesian product of the lesson-lists of the two
                # courses, obtained by the indexes i and j.
                for i_lesson in [l for l in one_per_day_courses[i].lessons if teacher in l.teachers]:
                    for j_lesson in [l for l in one_per_day_courses[j].lessons if teacher in l.teachers]:
                        # Ensure, the two lessons take place on different weekdays.
                        model.AddAllDifferent([i_lesson.weekdayVar, j_lesson.weekdayVar])

                        linConstraintCount += 1

                        # Skip after first lesson of course j if all lessons of it take place on
                        # the same day, which is the case if it is a AllInOneBlock course.
                        if one_per_day_courses[j].all_in_one_block:
                            break
                    # Skip after first lesson of course i if ... "see above".
                    if one_per_day_courses[i].all_in_one_block:
                        break

        # Alternate implementation with itertools combination and cartesian product functions.
        # But without the (in practice extremely insignificant) OneCoursePerDay optimization.
        # for courseTuple in itertools.combinations(one_per_day_courses, 2):
        #     lessons1 = list(filter(lambda l: teacher in l.teachers, courseTuple[0]))
        #     lessons2 = list(filter(lambda l: teacher in l.teachers, courseTuple[1]))
        #     for lessonTuple in itertools.product(lessons1, lessons2):
        #         model.Add(lessonTuple[0].weekdayVar != lessonTuple[1].weekdayVar)

    logger.logVariables("OneCoursePerDayPerTeacherConstraints", 0, linConstraintCount, 0)
    return 0, linConstraintCount, 0
