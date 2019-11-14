from SoftConstraintWeights import *  # Import the Constraints weights.
import logging
from ortools.sat.python.cp_model import CpModel, LinearExpr
import ORM
from Timeslot import Timeslot

logger = logging.getLogger("TimeTablingLogger")

"""
This Python file contains all the functions to add all the soft constraints of the timetable to the
OR-Tools model. The functions get a CpModel object and a reference to the ORM script.
The function createObjectiveFunctionSummands in this file will call all necessary functions to
create all variables for the soft constraints. It will create and return a list of OR-Tools
LinearExpr objects, called summands. Use this summands list to create the Objective.
E.g. model.Minimize(LinearExpr.Sum(summands))
"""

# First version of addCountLessonsAtNthHourVariable specialized for 6th Timeslot.
# Seems not to be faster than the general version if used the general version for all
# first, fifth and sixth hour count.
# But can used without the timeslotBoolVars helper variables.
# def addCountLessonsAtSixthHourVariable(model: CpModel, orm: ORM) -> IntVar:
#     variableCount = 0
#     otherConstraintCount = 0
#     linConstraintCount = 0
#     sixthHourCount = model.NewIntVar(0, len(orm.getLessons()), "sixthHourCount")
#     variableCount += 1
#     for lesson in orm.getLessons():
#         lesson.inSixthHour = model.NewBoolVar("")
#         variableCount += 1
#
#         model.Add(lesson.hourNumberVar + lesson.timeslot_size - 1 >= 6).OnlyEnforceIf(lesson.inSixthHour)
#         model.Add(lesson.hourNumberVar + lesson.timeslot_size - 1 < 6).OnlyEnforceIf(lesson.inSixthHour.Not())
#         linConstraintCount += 2
#     model.Add(sixthHourCount == LinearExpr.Sum(list(map(lambda l: l.inSixthHour, orm.getLessons()))))
#     for lesson in orm.getLessons():
#         del lesson.inSixthHour
#     linConstraintCount += 1
#     logger.debug("  %-45s Variables: %4i, LinearConstraints: %4i, OtherConstraints: %4i", "CountLessonsAtSixthHour:", variableCount, linConstraintCount, otherConstraintCount)
#
#    return sixthHourCount


# First version of addCountLessonsAtNthHourVariable specialized for 5th Timeslot.
# Seems not to be faster than the general version if used the general version for all
# first, fifth and sixth hour count.
# But can used without the timeslotBoolVars helper variables.
# def addCountLessonsAtFifthHourVariable(model: CpModel, orm):
#     variableCount = 0
#     otherConstraintCount = 0
#     linConstraintCount = 0
#     fifthHourCount = model.NewIntVar(0, len(orm.getLessons()), "fifthHourCount")
#     variableCount += 1
#     for lesson in orm.getLessons():
#         lesson.inFifthHour = model.NewBoolVar("")
#         variableCount += 1
#         model.AddLinearConstraint(lesson.hourNumberVar, 5 - (lesson.timeslot_size - 1), 5).OnlyEnforceIf(lesson.inFifthHour)
#         if lesson.timeslot_size == 1:
#             model.Add(5 != lesson.hourNumberVar).OnlyEnforceIf(lesson.inFifthHour.Not())
#         else:
#             model.Add(lesson.hourNumberVar < 5 - (lesson.timeslot_size - 1)).OnlyEnforceIf(lesson.inFifthHour.Not())
#         linConstraintCount += 2
#     model.Add(fifthHourCount == LinearExpr.Sum(list(map(lambda l: l.inFifthHour, orm.getLessons()))))
#     linConstraintCount += 1
#     logger.debug("  %-45s Variables: %4i, LinearConstraints: %4i, OtherConstraints: %4i", "CountLessonsAtFifthHour:", variableCount, linConstraintCount, otherConstraintCount)
#
#     return fifthHourCount


def addCountLessonsAtNthHour(model: CpModel, orm, timeslotNumber):
    """
    This function creates an IntVar that will contain the number of lessons that
    take place at a certain hour-number. Hour-number means a number of a timeslot
    of a day. Will count all lessons that occupy one of the timeslots with the given
    number.

    Args:
        model(CpModel):         The or-tools model for constraint programming optimization.
        orm(ORM):               The object-relation-mapper script that contains lists with
                                all data of the timetable.
        timeslotNumber(int):    The number of the timeslot on each day to count the lessons at.
                                Has to be >= 1 and <= TIMESLOTS_PER_DAY. Where TIMESLOTS_PER_DAY is
                                the number of timeslots in the timetable that take place per day.

    Returns:
        nthHourCount(IntVar):   The OR-Tools variable, containing the count of lessons at the given
                                timeslotNumber.
    """

    # Count created variables and constraints added to the CpModel for debugging and testing.
    variableCount = 0
    linConstraintCount = 0

    # Create variable for counting the number of lessons.
    nthHourCount = model.NewIntVar(0, len(orm.getLessons()), "nthHourCount")
    variableCount += 1

    # Collect all BoolVars of all lessons, that indicate if the lesson
    # take place at a certain timeslot.
    boolVars = []

    for lesson in orm.getLessons():
        #  Find the timeslots with the given timeslot number.
        for timeslot in [t for t in orm.getTimeslots() if t.number == timeslotNumber]:
            #  Collect the timeslotBoolVar for the given timeslot.
            boolVars.append(lesson.timeslotBoolVars[timeslot.id - 1])  # Timeslot IDs start at 1 but list index with 0.

    #  Assign the sum of the collected BoolVars to the target variable.
    model.Add(nthHourCount == LinearExpr.Sum(boolVars))
    linConstraintCount += 1

    logger.logVariables("CountLessonsAt" + str(timeslotNumber) + "Hour", variableCount, linConstraintCount, 0)

    return nthHourCount


def addCountGapsVariables(model: CpModel, orm: ORM):
    """
    This function creates variables for each SemesterGroup object that count the number of
    certain gaps in their timetable. A gap od size 1 is defined as timeslot at which no lesson with
    the semester group takes place, but at both adjacent timeslots take lesson with the semester
    group place. There are also gaps with size 2, 3 and 4 timeslots possible. This function depends
    on a timetable with 6 timeslots per day.

    The created variables for each gap size are appended to each SemesterGroup object.
    The type of this variables is IntVar. The names will be oneGapCount, twoGapCount, threeGapCount
    and fourGapCount.

    Args:
        model(CpModel):         The or-tools model for constraint programming optimization.
        orm(ORM):               The object-relation-mapper script that contains lists with
                                all data of the timetable.
    """

    # Count created variables and constraints added to the CpModel for debugging and testing.
    variableCount = 0
    otherConstraintCount = 0
    linConstraintCount = 0

    # Add bool vars for every semester group and every timeslot. They will indicate if a lesson,
    # the semester group participates at, takes place at the respective timeslot.
    # The variables are stored as dictionaries at each SemesterGroup object.
    for sg in orm.getSemesterGroups():
        sg.timeslotOccupiedMap = {}  # Map with Timeslot as keys and the respective BoolVar as value.

        for timeslot in orm.getTimeslots():
            # Collect boolVars for the current timeslot of all Lessons of the semester group.
            lessonTimeslotBoolVars = []
            for lesson in sg.getLessons():  # timeslots IDs start with 1, so subtract 1 for list index.
                lessonTimeslotBoolVars.append(lesson.timeslotBoolVars[timeslot.id - 1])

            # Create var that indicates if the semester group
            # has a lesson at the respective timeslot.
            tOccupied = model.NewBoolVar("")
            variableCount += 1
            # Add constraints to fulfill: tOccupied == OR(lessonTimeslotBoolVars)
            # tOccupied shall be True if one of the timeslotBoolVars in the created list is True.
            model.AddBoolOr(lessonTimeslotBoolVars).OnlyEnforceIf(tOccupied)
            model.AddBoolAnd([b.Not() for b in lessonTimeslotBoolVars]).OnlyEnforceIf(tOccupied.Not())
            otherConstraintCount += 2
            sg.timeslotOccupiedMap[timeslot] = tOccupied

    # Create variables for all possible gaps at all possible timeslots a gap can appear.
    for sg in orm.getSemesterGroups():
        oneGaps = []  # List with variables for all possible gaps of 1 timeslot.
        twoGaps = []  # List with variables for all possible gaps of 2 timeslots.
        threeGaps = []  # ""
        fourGaps = []  # ""

        for day in range(orm.WEEKDAYS):  # Iterate from monday to friday as index 0 .. 4
            # Create variables for all gaps of size 1 on the current day.
            for i in range(1, orm.TIMESLOTS_PER_DAY - 1):  # Iterate from 2nd to 2nd last hour.
                # Var for gap at timeslot i on day.
                gap = model.NewBoolVar("")
                # Select the timeslot before the gap, at the gap and after it.
                timeslotBefore = orm.getTimeslots()[day * orm.TIMESLOTS_PER_DAY + i - 1]
                timeslot = orm.getTimeslots()[day * orm.TIMESLOTS_PER_DAY + i]
                timeslotAfter = orm.getTimeslots()[day * orm.TIMESLOTS_PER_DAY + i + 1]
                # There has to be a lesson for the semester group before and after but not at the
                # timeslot of the gap.
                # gap => [x][ ][x]
                model.AddBoolAnd([sg.timeslotOccupiedMap[timeslotBefore],
                                  sg.timeslotOccupiedMap[timeslot].Not(),
                                  sg.timeslotOccupiedMap[timeslotAfter]]).OnlyEnforceIf(gap)
                # If no lesson before, a lesson at or no lesson after the timeslot of the gap, there
                # is no gap.
                model.AddBoolOr([sg.timeslotOccupiedMap[timeslotBefore].Not(),
                                 sg.timeslotOccupiedMap[timeslot],
                                 sg.timeslotOccupiedMap[timeslotAfter].Not()]).OnlyEnforceIf(gap.Not())
                oneGaps.append(gap)  # Add gapVar to List.
                variableCount += 1
                otherConstraintCount += 2

            # Create variables for all gaps of size 2 on the current day.
            for i in range(1, orm.TIMESLOTS_PER_DAY - 2):  # Iterate from 2nd to 3rd last hour. (Starts of gaps of size 2)
                gap = model.NewBoolVar("")
                # Select the timeslots before the gap, of the gap, at the gap and after it.
                timeslotBefore = orm.getTimeslots()[day * orm.TIMESLOTS_PER_DAY + i - 1]
                timeslot1 = orm.getTimeslots()[day * orm.TIMESLOTS_PER_DAY + i]
                timeslot2 = orm.getTimeslots()[day * orm.TIMESLOTS_PER_DAY + i + 1]
                timeslotAfter = orm.getTimeslots()[day * orm.TIMESLOTS_PER_DAY + i + 2]
                # gap => [x][ ][ ][x]
                model.AddBoolAnd([sg.timeslotOccupiedMap[timeslotBefore],
                                  sg.timeslotOccupiedMap[timeslot1].Not(),
                                  sg.timeslotOccupiedMap[timeslot2].Not(),
                                  sg.timeslotOccupiedMap[timeslotAfter]]).OnlyEnforceIf(gap)
                model.AddBoolOr([sg.timeslotOccupiedMap[timeslotBefore].Not(),
                                 sg.timeslotOccupiedMap[timeslot1],
                                 sg.timeslotOccupiedMap[timeslot2],
                                 sg.timeslotOccupiedMap[timeslotAfter].Not()]).OnlyEnforceIf(gap.Not())
                twoGaps.append(gap)
                variableCount += 1
                otherConstraintCount += 2

            for i in range(1, orm.TIMESLOTS_PER_DAY - 3):  # Iterate from 2nd to 4th last hour. (Starts of gaps of size 3)
                gap = model.NewBoolVar("")
                timeslotBefore = orm.getTimeslots()[day * orm.TIMESLOTS_PER_DAY + i - 1]
                timeslot1 = orm.getTimeslots()[day * orm.TIMESLOTS_PER_DAY + i]
                timeslot2 = orm.getTimeslots()[day * orm.TIMESLOTS_PER_DAY + i + 1]
                timeslot3 = orm.getTimeslots()[day * orm.TIMESLOTS_PER_DAY + i + 2]
                timeslotAfter = orm.getTimeslots()[day * orm.TIMESLOTS_PER_DAY + i + 3]
                # gap => [x][ ][ ][ ][x]
                model.AddBoolAnd([sg.timeslotOccupiedMap[timeslotBefore],
                                  sg.timeslotOccupiedMap[timeslot1].Not(),
                                  sg.timeslotOccupiedMap[timeslot2].Not(),
                                  sg.timeslotOccupiedMap[timeslot3].Not(),
                                  sg.timeslotOccupiedMap[timeslotAfter]]).OnlyEnforceIf(gap)
                model.AddBoolOr([sg.timeslotOccupiedMap[timeslotBefore].Not(),
                                 sg.timeslotOccupiedMap[timeslot1],
                                 sg.timeslotOccupiedMap[timeslot2],
                                 sg.timeslotOccupiedMap[timeslot3],
                                 sg.timeslotOccupiedMap[timeslotAfter].Not()]).OnlyEnforceIf(gap.Not())
                threeGaps.append(gap)
                variableCount += 1
                otherConstraintCount += 2
            for i in range(1, orm.TIMESLOTS_PER_DAY - 4):  # Iterate from 2nd to 5th last hour. (Starts of gaps of size 4)
                gap = model.NewBoolVar("")
                timeslotBefore = orm.getTimeslots()[day * orm.TIMESLOTS_PER_DAY + i - 1]
                timeslot1 = orm.getTimeslots()[day * orm.TIMESLOTS_PER_DAY + i]
                timeslot2 = orm.getTimeslots()[day * orm.TIMESLOTS_PER_DAY + i + 1]
                timeslot3 = orm.getTimeslots()[day * orm.TIMESLOTS_PER_DAY + i + 2]
                timeslot4 = orm.getTimeslots()[day * orm.TIMESLOTS_PER_DAY + i + 3]
                timeslotAfter = orm.getTimeslots()[day * orm.TIMESLOTS_PER_DAY + i + 4]
                # gap => [x][ ][ ][ ][ ][x]
                model.AddBoolAnd([sg.timeslotOccupiedMap[timeslotBefore],
                                  sg.timeslotOccupiedMap[timeslot1].Not(),
                                  sg.timeslotOccupiedMap[timeslot2].Not(),
                                  sg.timeslotOccupiedMap[timeslot3].Not(),
                                  sg.timeslotOccupiedMap[timeslot4].Not(),
                                  sg.timeslotOccupiedMap[timeslotAfter]]).OnlyEnforceIf(gap)
                model.AddBoolOr([sg.timeslotOccupiedMap[timeslotBefore].Not(),
                                 sg.timeslotOccupiedMap[timeslot1],
                                 sg.timeslotOccupiedMap[timeslot2],
                                 sg.timeslotOccupiedMap[timeslot3],
                                 sg.timeslotOccupiedMap[timeslot4],
                                 sg.timeslotOccupiedMap[timeslotAfter].Not()]).OnlyEnforceIf(gap.Not())
                fourGaps.append(gap)
                variableCount += 1
                otherConstraintCount += 2

        # Create vars for counting the number of gaps.
        sg.oneGapCount = model.NewIntVar(0, len(oneGaps), "")
        sg.twoGapCount = model.NewIntVar(0, len(twoGaps), "")
        sg.threeGapCount = model.NewIntVar(0, len(threeGaps), "")
        sg.fourGapCount = model.NewIntVar(0, len(fourGaps), "")
        variableCount += 4

        # Add constraints for assigning the gapCount vars.
        # Sum of boolVars of all gaps.
        model.Add(sg.oneGapCount == sum(oneGaps))
        model.Add(sg.twoGapCount == sum(twoGaps))
        model.Add(sg.threeGapCount == sum(threeGaps))
        model.Add(sg.fourGapCount == sum(fourGaps))
        linConstraintCount += 4

    logger.logVariables("GapVariables", variableCount, linConstraintCount, otherConstraintCount)


def addGapBetweenDaysTeacherVariables(model: CpModel, orm):
    """
    This function creates variables for each possible gap of days. One day gap, two day gap and
    three day gap. These gaps are only of the view of timetables of teachers. And the variables
    are only created for teachers with enabled avoid_free_day_gaps flag. On these Teacher objects,
    variables oneDayGaps, twoDayGaps ans threeDayGaps of the type IntVar, are added in this function.

    Args:
        model(CpModel):         The or-tools model for constraint programming optimization.
        orm(ORM):               The object-relation-mapper script that contains lists with
                                all data of the timetable.
    """

    # Count created variables and constraints added to the CpModel for debugging and testing.
    variableCount = 0
    linConstraintCount = 0
    otherConstraintCount = 0

    # Iterate over teachers with the avoid_free_day_gaps flag set.
    for teacher in filter(lambda t: t.avoid_free_day_gaps and len(t.lessons) > 1, orm.getTeachers()):
        # Create a list with BoolVars for the teacher and each weekday.
        # Each BoolVar will indicate if at least a lesson takes place on the respective day.
        workingDayBools = [model.NewBoolVar("") for x in range(orm.WEEKDAYS)]
        # Create a negated variant of each BoolVar since _NotBooleanVariable type is not allowed
        # for the MinEquality Constraint. (Maybe a bug in the Python implementation of OR-Tools)
        workingDayBoolsNeg = [model.NewBoolVar("") for x in range(orm.WEEKDAYS)]
        variableCount += 2 * len(workingDayBools)

        # Add assignments for each day and the respective variables.
        for i in range(orm.WEEKDAYS):
            # workingDayBool for the weekday of index i shall be True if at least of the teachers
            # lessons takes place at the respective weekday.
            # Make: workingDayBools[i] <==> lesson_1.weekdayBoolVars[i] OR lesson_2.weekdayBoolVars[i] OR ... OR lesson_n.weekdayBoolVars[i]
            model.AddMaxEquality(workingDayBools[i], [l.weekdayBoolVars[i] for l in teacher.lessons])
            # Assign negative variants.
            model.Add(workingDayBoolsNeg[i] == workingDayBools[i].Not())
            otherConstraintCount += 1
            linConstraintCount += 1

        # Create a BoolVar variable for each possible day gap.
        # Only on tuesday, wednesday or thursday, day gaps can occur. Or more general said, on
        # the second to the second last day of the week.
        # Day gaps of size 1:
        # Gap on tuesday, means lessons on monday and wednesday but not on tuesday.
        oneDayGaps = []
        for dayIndex in range(1, orm.WEEKDAYS - 1):
            oneDayGap = model.NewBoolVar("One_Day_Gap")
            # Add constraints for assigning the gap variables.
            model.AddMinEquality(oneDayGap, [workingDayBools[dayIndex - 1],
                                             workingDayBoolsNeg[dayIndex],
                                             workingDayBools[dayIndex + 1]])
            # E.g.: tuesdayGap <==> lessonOnMonday    AND lessonOnTuesday.Not()   AND lessonOnWednesday
            oneDayGaps.append(oneDayGap)

            variableCount += 1
            otherConstraintCount += 1

        # Day gaps of size 2:
        # Gap on tuesday and wednesday, means lessons on monday and thursday but not on tuesday
        # and wednesday.
        twoDayGaps = []
        for dayIndex in range(1, orm.WEEKDAYS - 2):
            twoDayGap = model.NewBoolVar("Two_Day_Gap")
            # Add constraints for assigning the gap variables.
            model.AddMinEquality(twoDayGap, [workingDayBools[dayIndex - 1],
                                             workingDayBoolsNeg[dayIndex],
                                             workingDayBoolsNeg[dayIndex + 1],
                                             workingDayBools[dayIndex + 2]])
            # E.g.: tue_wedGap <==> lessonOnMonday AND lessonOnTuesday.Not() AND lessonOnWednesday.Not() AND lessonOnThursday
            twoDayGaps.append(twoDayGap)

            variableCount += 1
            otherConstraintCount += 1

        # Day gaps of size 3:
        # Gap on tuesday, wednesday and thursday, means lessons on monday and friday but not on
        # tuesday, wednesday, thursday.
        threeDayGaps = []
        for dayIndex in range(1, orm.WEEKDAYS - 3):
            threeDayGap = model.NewBoolVar("Three_Day_Gap")
            # Add constraints for assigning the gap variables.
            model.AddMinEquality(threeDayGap, [workingDayBools[dayIndex - 1],
                                               workingDayBoolsNeg[dayIndex],
                                               workingDayBoolsNeg[dayIndex + 1],
                                               workingDayBoolsNeg[dayIndex + 2],
                                               workingDayBools[dayIndex + 3]])
            # E.g.: tue_wed_thuGap <==> lessonOnMonday AND eventOnTuesday.Not() AND lessonOnWednesday.Not() AND lessonOnThursday.Not() AND lessonOnFriday
            threeDayGaps.append(threeDayGap)

            variableCount += 1
            otherConstraintCount += 1

        # Create and assign the gapCount variables.
        teacher.oneDayGapCount = model.NewIntVar(0, len(oneDayGaps), "")
        # In fact, the maximum number of gaps of size 1 is much smaller than len(oneDayGaps) because
        # some gaps are mutually exclusive. E.g. there cannot be a one day gap on tuesday and
        # wednesday. But use this to large upper bound to avoid determining the actual maximum number.
        model.Add(teacher.oneDayGapCount == sum(oneDayGaps))

        teacher.twoDayGapCount = model.NewIntVar(0, len(twoDayGaps), "")
        model.Add(teacher.twoDayGapCount == sum(twoDayGaps))

        teacher.threeDayGapCount = model.NewIntVar(0, len(threeDayGaps), "")
        model.Add(teacher.threeDayGapCount == sum(threeDayGaps))

        variableCount += 3
        otherConstraintCount += 3

    logger.logVariables("TeacherAvoidFreeDaysBetweenWorkingDays", variableCount, linConstraintCount, otherConstraintCount)


def addFreeDaySemesterGroupVariables(model: CpModel, orm):
    """
    This function creates variables for each semester group that wishes a free day. Which means
    the variable free_day of the SemesterGroup object is not None. In that case, a variable
    lessonsOnFreeDay is added to the SemesterGroup object. This variable will indicate the number
    of lessons, the semester group is participating at, take place at the wished free day. This is
    not equivalent to the number of occupied timeslots for the group on that day.

    The value of the free_day variable - if not None - has to be one of the constants in file
    Timeslot.py, indicating a weekday. E.g. 'MO' for monday.

    Args:
        model(CpModel):         The or-tools model for constraint programming optimization.
        orm(ORM):               The object-relation-mapper script that contains lists with
                                all data of the timetable.
    """

    # Count created variables and constraints added to the CpModel for debugging and testing.
    variableCount = 0
    linConstraintCount = 0

    # Filter and iterate over semester groups with a wished free day.
    for group in [sg for sg in orm.getSemesterGroups() if sg.free_day is not None]:
        freeDayId = Timeslot.getWeekdayID(group.free_day)  # Get the weekday number of the free day.
        group.lessonsOnFreeDay = model.NewIntVar(0, group.max_lessons_per_day, "")  # Create the var.
        variableCount += 1
        # Collect all weekdayBoolVars of all lessons of the semester group and the specific weekday.
        boolVarsOnFreeDay = [l.weekdayBoolVars[freeDayId - 1] for l in group.getLessons()]
        model.Add(group.lessonsOnFreeDay == sum(boolVarsOnFreeDay))
        linConstraintCount += 1

    logger.logVariables("CountLessonsOnFreeDay:", variableCount, linConstraintCount, 0)


def createObjectiveFunctionSummands(model: CpModel, orm):
    """
    This function builds a list with all summands of the objective function.
    For this purpose it calls also all individual functions for the soft
    constraints in this file.
    It adds the weights to the soft constraints fulfillment variables as
    the objective-function-objects and collects them all in a list.
    This list, called 'summands', is returned as first return value.

    Args:
        model(CpModel): The or-tools model for constraint programming optimization.
        orm(ORM):       The object-relation-mapper script that contains lists with
                        all data of the timetable.

    Returns:
        summands(list[LinearExpr]): The list with summands of the objective function.
        sixthHourCount(IntVar):     The IntVar, containing the number of lessons in the
                                    sixth timeslot of a day.
        fifthHourCount(IntVar):     The IntVar, containing the number of lessons in the
                                    fifth timeslot of a day.
        firstHourCount(IntVar):     The IntVar, containing the number of lessons in the
                                    first timeslot of a day.
    """

    # To dynamically create the objective function, create a list for all summands in the function.
    summands = []  # List of all summands of the objective function.

    # Add summands for all optional constraints:

    # ### PreferFirstStudyDayChoiceConstraint ###
    # Prefer first studyday choice.
    # Use the studyDay1BoolVar variable to indicate if the first studyday was applied.
    # Take only teachers with a studyday and with lessons.
    for teacher in filter(lambda t: t.hasStudyday() and t.lessons, orm.getTeachers()):
        summands.append(teacher.studyDay1BoolVar.Not() * PREFER_FIRST_STUDYDAY_PENALTY)

    # ### AvoidLateTimeslotsConstraint ###
    # Avoid the sixth hour.
    sixthHourCount = addCountLessonsAtNthHour(model, orm, 6)
    summands.append(sixthHourCount * SIXTH_HOUR_PENALTY)
    # Avoid the fifth hour.
    fifthHourCount = addCountLessonsAtNthHour(model, orm, 5)
    summands.append(fifthHourCount * FIFTH_HOUR_PENALTY)

    # ### AvoidEarlyTimeslotsConstraint ###
    # Avoid the first hour.
    firstHourCount = addCountLessonsAtNthHour(model, orm, 1)
    summands.append(firstHourCount * FIRST_HOUR_PENALTY)

    # ### AvoidGapBetweenLessonsSemesterGroupConstraint ###
    addCountGapsVariables(model, orm)
    for sg in orm.getSemesterGroups():
        summands.append(sg.oneGapCount * ONE_TIMESLOT_GAP_PENALTY)
        summands.append(sg.twoGapCount * TWO_TIMESLOT_GAP_PENALTY)
        summands.append(sg.threeGapCount * THREE_TIMESLOT_GAP_PENALTY)
        summands.append(sg.fourGapCount * FOUR_TIMESLOT_GAP_PENALTY)

    # ### AvoidGapBetweenDaysTeacherConstraint ###
    # gaps between working days for teacher with avoid_free_days_between_working_days == True
    addGapBetweenDaysTeacherVariables(model, orm)
    for teacher in filter(lambda t: hasattr(t, "oneDayGapCount"), orm.getTeachers()):
        summands.append(teacher.oneDayGapCount * ONE_DAY_GAP_PENALTY)
        summands.append(teacher.twoDayGapCount * TWO_DAY_GAP_PENALTY)
        summands.append(teacher.threeDayGapCount * THREE_DAY_GAP_PENALTY)

    # ### FreeDaySemesterGroupConstraint ###
    # semester groups free day
    addFreeDaySemesterGroupVariables(model, orm)
    for sg in filter(lambda sg: sg.free_day is not None, orm.getSemesterGroups()):
        summands.append(sg.lessonsOnFreeDay * LESSONS_ON_FREE_DAY_PENALTY)

    return summands, sixthHourCount, fifthHourCount, firstHourCount
