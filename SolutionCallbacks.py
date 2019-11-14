import logging
import traceback
from ortools.sat.python import cp_model
import SolutionValidation
from Solution import Solution
import time

logger = logging.getLogger("TimeTablingLogger")


class TimeTablePrinter(cp_model.CpSolverSolutionCallback):
    """
    This callback will be used during the normal timetabling search.
    It counts the number of solutions, can print every found solution
    or the last solution after the search. If not every solution is
    printed during the search and the search is optimized, it will
    print the progress of the objective value.

    In debug mode, it will also print the timetable in view of every teacher
    and every semester group.
    """

    def __init__(self, orm, printEverySolution, optimize=False, debug=False):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__solution_count = 0
        self.print = printEverySolution
        self.optimize = optimize
        self.orm = orm
        self.lessons = orm.getLessons()
        self.timeslots = orm.getTimeslots()
        self.daymap = createDaymap(self.timeslots)
        self.startOV = None
        self.startTime = time.time_ns()
        self.lastTime = -1
        self.debug = debug

    def OnSolutionCallback(self):
        """
        Callback will be called for each solution found.
        """
        self.__solution_count += 1
        self.lastTime = time.time_ns() - self.startTime  # Store time of last solution found.
        if self.print:
            printTimeTable(self, daymap=self.daymap, lessons=self.lessons, solutionIndex=self.__solution_count)
        else:  # Print objective progress.
            if self.__solution_count == 1 and self.optimize:  # First solution
                self.startOV = self.ObjectiveValue()
                print("Objective Value Progression:")
            if self.optimize and self.startOV != 0:
                print("_" * int(75 * (self.ObjectiveValue() / self.startOV)), "%i (Solution: %i)" % (self.ObjectiveValue(), self.__solution_count))

    def SolutionCount(self):
        return self.__solution_count

    def PrintTimeTable(self):
        # Call this method after end of search to print the last solution found.
        printTimeTable(self, daymap=self.daymap, lessons=self.lessons, solutionIndex=self.__solution_count, printTeacherTables=self.debug, printSemesterGroupTables=self.debug)


class SolutionValidator(cp_model.CpSolverSolutionCallback):
    """
    Call back used for solution validation.
    Will store every solution as Solution object and validates it during the search.
    Number of invalid solutions can be get by the method InvalidCount().
    """

    def __init__(self, orm):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__invalidCount = 0
        self.__solution_count = 0
        self.orm = orm
        self.timeslotMap = createTimeslotMap(orm.getTimeslots())
        self.roomMap = createRoomMap(orm.getRooms())
        self.dayMap = createDaymap(orm.getTimeslots())

    def OnSolutionCallback(self):
        self.__solution_count += 1
        # Build solution object.
        sol = Solution(self.__solution_count, self.orm, self.ObjectiveValue())
        sol.callback = self
        for lesson in self.orm.getLessons():
            for tVar in lesson.timeVars:
                sol.addLesson(lesson, self.roomMap[self.Value(lesson.roomVar)], self.timeslotMap[self.Value(tVar)])
        # Validate solution object.
        try:
            if not SolutionValidation.validateSolution(sol):  # print the TimeTable if the solution is invalid
                printTimeTable(self, self.dayMap, self.SolutionCount(), self.orm.getLessons())
                logger.debug("Invalidations found in solution %i\n\n" % self.__solution_count)
                self.__invalidCount += 1
        except Exception as e:
            print(traceback.format_exc())
            raise e

    def SolutionCount(self):
        return self.__solution_count

    def InvalidCount(self):
        return self.__invalidCount


class SolutionCounter(cp_model.CpSolverSolutionCallback):
    """
    Rudimentary solution callback that just counts the solutions.
    """

    def __init__(self):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__solution_count = 0

    def OnSolutionCallback(self):
        self.__solution_count += 1

    def SolutionCount(self):
        return self.__solution_count


# Used for debugging the gap variables:
# class GapVarPrinter(TimeTablePrinter):
#     def __init__(self, lessons, timeslots, printEverySolution, sgs):
#         TimeTablePrinter.__init__(self, lessons, timeslots, printEverySolution)
#         self.sgs = sgs
#
#     def OnSolutionCallback(self):
#         TimeTablePrinter.OnSolutionCallback(self)
#         for sg in self.sgs:
#             for k, v in sg.gapVarMap.items():
#                 print("%s : %s, %i" % (k, str(self.Value(v[0])), self.Value(v[1])))


"""
    Helper functions for the TimeTable printing
"""


def printTimeTable(sCallback, daymap, solutionIndex, lessons, printTeacherTables=False, printSemesterGroupTables=False):
    """
    Prints a timetable to the console.
    Args:
        sCallback: A cp_model.CpSolverSolutionCallback object.
        daymap: A map of the timetable days, created by the function createDaymap(timeslots) in this file.
        solutionIndex: Number of the solution to print.
        lessons: List with all lessons of the timetable.
        printTeacherTables: Set to True to print the timetable of the view of every teacher.
        printSemesterGroupTables: Set to True to print the timetable of the view of every semester group.
    """
    try:
        print("\n\n<<< Solution %i: OV = %i >>>" % (solutionIndex, sCallback.ObjectiveValue()))

        maxLine = printTimeTableAll(sCallback, daymap, lessons)

        if printTeacherTables:
            printTeacherTimeTables(sCallback, daymap, maxLine)

        if printSemesterGroupTables:
            printSemesterGroupTimeTables(sCallback, daymap, maxLine)

        print()
    except Exception as e:
        print(e)
        print(traceback.format_exc())


def printTimeTableAll(sCallback, daymap, lessons):
    """
    Prints a timetable with the lessons of all teachers / semester groups.
    Args:
        sCallback: A cp_model.CpSolverSolutionCallback object.
        daymap: A map of the timetable days, created by the function createDaymap(timeslots) in this file.
        lessons: List with all lessons of the timetable.

    Returns: Maximum line size printed.
    """
    maxLine = 0
    courseNameLength = 1 + max(len(c.name) for c in sCallback.orm.getCourses())
    for day in daymap:
        print("------------------ %s ------------------" % day)
        for t in daymap[day]:
            print(t)
            for l in lessons:
                if t.id in map(lambda t: sCallback.Value(t), l.timeVars):
                    line = createLessonLine(l, sCallback, courseNameLength)
                    print(line)
                    # Used for debugging.
                    # print(list(map(lambda v: sCallback.Value(v), l.timeslotBoolVars)))
                    # print("day: %i number: %i" % (sCallback.Value(l.weekdayVar), sCallback.Value(l.hourNumberVar)))
                    if len(line) > maxLine:
                        maxLine = len(line)
    print(maxLine * "_")
    return maxLine


def printTeacherTimeTables(sCallback, daymap, maxLine):
    """
    Prints the timetables for all teachers.
    Args:
        sCallback: A cp_model.CpSolverSolutionCallback object.
        daymap: A map of the timetable days, created by the function createDaymap(timeslots) in this file.
        maxLine: Length of separation line after each timetable.
    """
    courseNameLength = 1 + max(len(c.name) for c in sCallback.orm.getCourses())
    for teacher in sCallback.orm.getTeachers():
        print("TimeTable for Teacher %i %s:" % (teacher.id, teacher.abbreviation))
        dayIndex = 0
        for day in daymap:
            print("------------------ %s ------------------" % day)
            for t in daymap[day]:
                print(t)
                for l in teacher.lessons:
                    if t.id in map(lambda t: sCallback.Value(t), l.timeVars):
                        line = createLessonLine(l, sCallback, courseNameLength)
                        print(line)
            # Used for debugging.
            # print("Lesson Times: %i" % sCallback.Value(teacher.sumTimeslotsPerDay[dayIndex]))
            # print("Lecture Times: %i" % sCallback.Value(teacher.sumLectureTimeslotsPerDay[dayIndex]))
            dayIndex += 1
        # Used for debugging.
        # li = list(map(lambda v: sCallback.Value(v), teacher.timeslotLectureBoolMap.values()))
        # print("Lecture take place map: %s" % [li[x:x + 6] for x in range(0, len(li), 6)])
        print(maxLine * "_")


def printSemesterGroupTimeTables(sCallback, daymap, maxLine):
    """
    Prints the timetables for all semester groups.
    Args:
        sCallback: A cp_model.CpSolverSolutionCallback object.
        daymap: A map of the timetable days, created by the function createDaymap(timeslots) in this file.
        maxLine: Length of separation line after each timetable.
    """
    courseNameLength = 1 + max(len(c.name) for c in sCallback.orm.getCourses())
    for sg in sCallback.orm.getSemesterGroups():
        print("TimeTable for SemesterGroup %i %s, %i:" % (sg.id, sg.study_course, sg.semester))
        dayIndex = 0
        for day in daymap:
            print("------------------ %s ------------------" % day)
            for t in daymap[day]:
                print(t)
                for l in sg.getLessons():
                    if t.id in map(lambda t: sCallback.Value(t), l.timeVars):
                        line = createLessonLine(l, sCallback, courseNameLength)
                        print(line)
            # Used for debugging.
            # print([sCallback.Value(weekdayBoolVar) for weekdayBoolVar in l.weekdayBoolVars])
            # print("Lesson Times: %i" % sCallback.Value(sg.sumTimeslotsPerDay[dayIndex]))
            dayIndex += 1
        print(maxLine * "_")


def createLessonLine(l, sCallback, courseNameLength) -> str:
    """
    Generates a line with a lesson and some information about that lesson.
    Prints: Course id, Lesson id, Lesson length, Lesson name.
            If lesson is PartGroupLesson or lecture.
            Room of the lesson, SemesterGroups, Teachers.
    Args:
        l: A lesson of the timetable
        sCallback: A cp_model.CpSolverSolutionCallback object.
        courseNameLength: Maximum length of course names, for good visual indentation.

    Returns: The generated line as string.
    """
    line = ("%41s (%2s,%3s)%3s %-" + str(courseNameLength) + "s %1s  %1s  R: %2i SG: %5s T: %2s") % \
           ("",  # start ident
            "%i" % l.course.id,  # course id of the lessons course
            "%i" % l.id,  # lesson id
            "[%i]" % l.timeslot_size,  # timeslot size of the lesson
            l.course.name,  # name of the lesson
            "P" if not l.whole_semester_group else "",  # P flag if the lesson is only for a part of the SemesterGroup
            "L" if l.course.is_lecture else "",  # L flag if the lesson is a lecture
            sCallback.Value(l.roomVar),  # id of the room the lessons takes place in
            ','.join(map(lambda g: str(g.id), l.course.semester_groups)),  # list of the SemesterGroups of the lesson
            # list of the Teachers of the Lesson, with the info which studyday of the Teacher is applied
            ', '.join(map(lambda t: "%2i(%s %s)" % (t.id, ((t.study_day_1 + ":" + str(sCallback.Value(t.studyDay1BoolVar))) if t.hasStudyday() else ""), ((t.study_day_2 + ":" + str(sCallback.Value(t.studyDay2BoolVar))) if t.hasStudyday() else "")), l.teachers))
            )
    return line


def createDaymap(timeslots):
    daymap = {}
    for t in timeslots:
        if t.weekday not in daymap:
            daymap[t.weekday] = []
        daymap[t.weekday].append(t)
    return daymap


def createTimeslotMap(timeslots):
    map = {}
    for timeslot in timeslots:
        map[timeslot.id] = timeslot
    return map


def createRoomMap(rooms):
    map = {}
    for room in rooms:
        map[room.id] = room
    return map
