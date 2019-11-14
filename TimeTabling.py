import argparse
import time
from ortools.sat.python import cp_model
from ortools.sat.python.cp_model import FEASIBLE, OPTIMAL, INFEASIBLE, UNKNOWN, MODEL_INVALID
import ExcelWriter
import Solution
import SolutionCallbacks
from HardConstraints import *
from SoftConstraints import *
from SolutionCallbacks import TimeTablePrinter, SolutionCounter, SolutionValidator
from HelperFunctions import t_or_f

# Save the time for finding the best solution in a global variable.
# So it can be retrieved when running the main function multiple times for performance analyzing.
bestSolutionTime = 0

"""
This file contains the entry for the timetable search.

"""
DEBUG = False

# Create logger object for printing to the console.
logger = logging.getLogger("TimeTablingLogger")
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
logger.addHandler(logging.StreamHandler())

# Program Variable Defaults.
# Constants for options of solution printing.
PRINT_NONE = 0
PRINT_BEST = 1
PRINT_ALL = 2


def getPrintSettingName(argument):
    # Maps a printing option value to its name.
    switch = {
        PRINT_NONE: "PRINT_NONE",
        PRINT_BEST: "PRINT_BEST",
        PRINT_ALL: "PRINT_ALL"
    }
    return switch.get(argument, "Invalid Setting")


#
# Set program variables here. The most of them can be set through the program
# arguments but this values are treated as default values if the arguments are not specified.
# ___________________________
# Option to search for optimal solution.
# Soft constraints will ignored if this value is set to False.
# Can be overwritten by the program parameters.
OPTIMIZE = True
# ___________________________
# Option to print the found solutions during the search.
PRINT_SOLUTIONS = PRINT_BEST
# ___________________________
# Stop search after n seconds.
# Search will also terminate when the optimal solution was found.
# Can be overwritten by the program parameters.
MAX_SEARCH_TIME = 300  # Seconds
# ___________________________
# Option to export the last found solution into an Excel file.
# Can be overwritten by the program parameters.
EXPORT_TIMETABLE = False
# ___________________________
# Option to search for all solutions. Only without optimization.
# This option is nonsensical for timetables that are not very small because
# the number of solutions is extremely large and the search process does not
# terminate very soon. Was only used in the early stages of development.
SEARCH_ALL = False
# ___________________________
# Set to True to validate each solution that was found.
# Will search for all solutions until the max search time is reached.
# Should only be used for debugging.
SEARCH_FOR_INVALIDS = False
#
# Names for the exported Excel file.
# Can be overwritten by the program parameters.
# Only characters are allowed that are also allowed
# as file names of the operating system used.
#
# Name of the university of the timetable.
universityName = "TH-Lübeck"
# Name of the timetable's department.
departmentName = "Elektrotechnik"
# String to represent the timetable's semester.
semesterName = "WiSe 2018-19"


def main():
    """
    Main function of the TimeTabling program.
    Reads the timetable data from database, creates the CpModel and solves it.
    If set, writes the last solution to an Excel file.
    """

    # Reference to the ORM script file. Used to access the timetable data.
    orm = ORM

    # Print the program settings to the console.
    logger.info("Program Settings:")
    logger.info("   PRINT_SOLUTIONS  = %s" % getPrintSettingName(PRINT_SOLUTIONS))
    logger.info("   MAX_SEARCH_TIME  = %i seconds" % MAX_SEARCH_TIME)
    logger.info("   OPTIMIZE         = %s" % OPTIMIZE)
    logger.info("   EXPORT_TIMETABLE = %s" % EXPORT_TIMETABLE)
    if SEARCH_FOR_INVALIDS:
        logger.info("SEARCH_FOR_INVALIDS: NO_OPTIMIZATION, SEARCH_FOR_ALL_SOLUTIONS, PRINT_ONLY_INVALIDS, 1 Thread")

    # Print information about numbers of the timetable data objects read form the database file.
    logger.info("\nData Statistics:")
    logger.info("   Teachers:       %4i" % len(orm.getTeachers()))
    logger.info("   Rooms:          %4i" % len(orm.getRooms()))
    logger.info("   SemesterGroups: %4i" % len(orm.getSemesterGroups()))
    logger.info("   Courses:        %4i" % len(orm.getCourses()))
    logger.info("   Lessons:        %4i" % len(orm.getLessons()))
    logger.info("   Lesson Hours:   %4i" % sum(map(lambda l: l.timeslot_size, orm.getLessons())))  # Number of Timeslots all Lessons occupy.

    if DEBUG:
        # Some plausibility checks of the timetable data.
        #
        # Print Teacher infos and run a plausibility check for the teachers data.
        logger.debug("\nTeacher Info:")
        for teacher in orm.getTeachers():
            logger.debug("   T: %2i %3s, LessonHours: %2i, HasStudyday: %i, AvailableTimeslots: %2i, "
                         "MaxLessonsPerDay: %i, MaxLecturesPerDay: %i, MaxLecturesAsBlock: %i, Lectur"
                         "eHours: %2i LongestLesson: %i, LongestLecture: %i, OneCoursePerDayPerTeache"
                         "r: %i" %
                         (teacher.id, teacher.abbreviation, sum(l.timeslot_size for l in teacher.lessons),
                          teacher.hasStudyday(),
                          5 * teacher.max_lessons_per_day - len(teacher.not_available_timeslots) - (6 if teacher.hasStudyday() else 0),
                          teacher.max_lessons_per_day, teacher.max_lectures_per_day,
                          teacher.max_lectures_as_block, sum(list(map(lambda l: l.course.is_lecture * l.timeslot_size, teacher.lessons))),
                          max(map(lambda l: l.timeslot_size, teacher.lessons)),
                          max(map(lambda l: l.timeslot_size if l.course.is_lecture else 0, teacher.lessons)),
                          len(list(filter(lambda c: c.one_per_day_per_teacher, teacher.getCourses()))))
                         )
            teacher.plausibilityCheck(orm, "      ")
        #
        # Print SemesterGroup infos.
        logger.debug("\nSemesterGroup Info:")
        for sg in orm.getSemesterGroups():
            logger.debug("   SG: %2i %-42s, LessonHours: %2i, MaxLessonsPerDay: %i" %
                         (sg.id, sg.study_course + " S" + str(sg.semester),
                          sum(l.timeslot_size for l in sg.getLessons()), sg.max_lessons_per_day))
        #
        # Run plausibility check for the courses data
        for course in orm.getCourses():
            course.plausibilityCheck(orm, "      ")

    #######################
    #  ####################
    #  TimeTable Search
    #  ####################
    #######################

    model = cp_model.CpModel()  # Create the empty CpModel.

    #  ####################
    #  Add Hard Constraints
    #  ####################
    # The most function calls can be commented out to disable certain constrains.

    logger.debug("\nHard Constraints:")

    # Create Basic Variables
    # Needed for the program to work.
    createLessonTimeAndRoomVariables(model, orm)

    # Create Helper Variables
    # Needed for the program to work.
    createLessonTimeHelperVariables(model, orm)
    createLessonTimeslotBoolHelperVariables(model, orm)
    createTeacherLectureAtTimeslotMap(model, orm)

    # Time Conflict Constraints
    addTeacherTimeConstraints(model, orm)
    addSemesterGroupTimeConstraints(model, orm)
    addRoomTimeConstraints(model, orm)

    # Max Per Day Constraints
    addMaxLessonsPerDayTeacherConstraints(model, orm)
    addMaxLessonsPerDaySemesterGroupConstraints(model, orm)
    addMaxLessonsPerDayCourseConstraints(model, orm)
    # Lecture Specific Constraints
    addMaxLecturesAsBlockTeacherConstraints(model, orm)  # !!! Needs call of addMaxLecturesPerDayTeacherConstraints after(!) calling this !!!
    addMaxLecturesPerDayTeacherConstraints(model, orm)

    # Other Constraints
    addTeacherStudyDayConstraints(model, orm)
    addRoomNotAvailableConstraints(model, orm)
    addCourseAllInOneBlockConstraints(model, orm)
    addConsecutiveLessonsConstraints(model, orm)
    addOneCoursePerDayPerTeacherConstraints(model, orm)

    # ##################################################
    # Add Variables and Constraints for Soft Constraints
    # ##################################################

    # No optimization when searching for all solutions possible.
    if OPTIMIZE and not SEARCH_FOR_INVALIDS and not SEARCH_ALL:
        logger.debug("\nSoft Constraints:")

        # List with all summands that represent the objective function.
        # Also save the variables to count the number of Lessons in the sixth, fifth and first
        # Timeslots for printing them at the end.
        summands, sixthCount, fifthCount, firstCount = createObjectiveFunctionSummands(model, orm)

        # Set the objective function as sum of all summands.
        model.Minimize(LinearExpr.Sum(summands))

    # ###########
    # Solve Model
    # ###########

    solver = cp_model.CpSolver()  # Create the CP-SAT solver.

    # Set the number of worker threads.
    # Only one thread allowed when searching for all solutions.
    # The effect on the time needed to find the best solution is somewhat strange.
    # More threads are not always better, even if the system supports more.
    # 4 seems to work well. (On a system with at least 4 processor threads)
    solver.parameters.num_search_workers = 1 if SEARCH_ALL or SEARCH_FOR_INVALIDS else 4
    # Set the max search time.
    solver.parameters.max_time_in_seconds = MAX_SEARCH_TIME

    # Print stats about the created CpModel.
    logger.debug("\nModel Statistics:")
    for line in model.ModelStats().split("\n"):
        logger.debug("  " + line)

    #
    # Start the search.
    #

    logger.info("\nStart Searching...\n")

    # Case of solution validation is set:
    if SEARCH_FOR_INVALIDS:
        solution_callback = SolutionValidator(orm)  # Set the validator callback.
        status = solver.SearchForAllSolutions(model, solution_callback)  # Start search.
        print("Invalid Solutions: %i" % solution_callback.InvalidCount())

    # Normal search case:
    else:
        # Initialize the solution callback (solution printer).
        # Takes arguments when to print a solution.
        solution_callback = TimeTablePrinter(orm, printEverySolution=PRINT_SOLUTIONS == PRINT_ALL,
                                             optimize=OPTIMIZE and not SEARCH_ALL, debug=DEBUG)

        # Call solve method on the solver.

        # Case of searching for all solutions:
        if SEARCH_ALL:
            status = solver.SearchForAllSolutions(model, solution_callback)

        # Case of searching one or the best solution:
        else:
            status = solver.SolveWithSolutionCallback(model, solution_callback)

        logger.info("\nSEARCH FINISHED\n")
        time.sleep(0.2)  # Wait for solution printer to not interfere with the logger.

        # After the search terminated, print the last solution that was found. (if any solution was found)
        if PRINT_SOLUTIONS == PRINT_BEST and (status is OPTIMAL or status is FEASIBLE):
            solution_callback.PrintTimeTable()

        if status is INFEASIBLE:
            logger.info("\nNo Timetable solution is possible. The model is infeasible!")
        elif status is UNKNOWN:
            logger.info("\nNo solution was found until the search time limit reached.")
        elif status is MODEL_INVALID:
            logger.error("\nError. Timetable data led to an invalid CpModel.")

    # ################
    # After the search
    # ################

    time.sleep(0.2)  # Wait for solution printer to not interfere with the logger.
    # Print stats of the search.
    logger.info('\nSearch Statistics:')
    logger.info('  Status          : %s' % solver.StatusName(status))
    logger.info('  SAT Booleans    : %i' % solver.NumBooleans())
    logger.debug('  Conflicts       : %i' % solver.NumConflicts())
    logger.debug('  Branches        : %i' % solver.NumBranches())
    logger.info('  Wall Time       : %f s' % solver.WallTime())
    logger.info('  Solutions Found : %i' % solution_callback.SolutionCount())
    if hasattr(solution_callback, "lastTime"):
        logger.info('  Approx. Time to best solution: %.3f s' % (solution_callback.lastTime/1e9))
        global bestSolutionTime
        bestSolutionTime = solution_callback.lastTime

    # Print infos about violations of the Soft Constraints.
    if OPTIMIZE and not SEARCH_ALL and not SEARCH_FOR_INVALIDS and (status is FEASIBLE or status is OPTIMAL):
        logger.info('\n\nTimetable Statistics:')
        studyDayTeachers = list(filter(lambda t: t.hasStudyday(), orm.getTeachers()))

        logger.info('  Objective Value : %i' % solver.ObjectiveValue())
        logger.info('  Studyday 2nd choices applied: %i/%i' % (sum(map(lambda t: solver.Value(t.studyDay1BoolVar.Not()), studyDayTeachers)), len(studyDayTeachers)))
        logger.info('  1. Hours:  %2i' % solver.Value(firstCount))
        logger.info('  5. Hours:  %2i' % solver.Value(fifthCount))
        logger.info('  6. Hours:  %2i' % solver.Value(sixthCount))
        logger.info('  Timeslot gaps for SemesterGroups:')
        logger.info('    One Timeslot:    %2i' % sum(map(lambda sg: solver.Value(sg.oneGapCount), orm.getSemesterGroups())))
        logger.info('    Two Timeslots:   %2i' % sum(map(lambda sg: solver.Value(sg.twoGapCount), orm.getSemesterGroups())))
        logger.info('    Three Timeslots: %2i' % sum(map(lambda sg: solver.Value(sg.threeGapCount), orm.getSemesterGroups())))
        logger.info('    Four Timeslots:  %2i' % sum(map(lambda sg: solver.Value(sg.fourGapCount), orm.getSemesterGroups())))
        logger.info('  Unwanted free day gaps for Teachers:')
        logger.info('    One Day:    %2i' % sum(map(lambda t: solver.Value(t.oneDayGapCount), filter(lambda t: t.avoid_free_day_gaps, orm.getTeachers()))))
        logger.info('    Two Days:   %2i' % sum(map(lambda t: solver.Value(t.twoDayGapCount), filter(lambda t: t.avoid_free_day_gaps, orm.getTeachers()))))
        logger.info('    Three Days: %2i' % sum(map(lambda t: solver.Value(t.threeDayGapCount), filter(lambda t: t.avoid_free_day_gaps, orm.getTeachers()))))
        logger.info('  Lessons on free SemesterGroup days: %i'% sum([solver.Value(sg.lessonsOnFreeDay) for sg in orm.getSemesterGroups() if sg.free_day]))

    # ################
    # TimeTable Export
    # ################

    # If set, export the timetable solution to Excel file.
    if EXPORT_TIMETABLE and (status is OPTIMAL or status is FEASIBLE):

        # Save the timetable as Solution object:

        sol = Solution.Solution(solution_callback.SolutionCount(), orm, solver.ObjectiveValue())
        roomMap = SolutionCallbacks.createRoomMap(orm.getRooms())  # Mapping from id to room object.
        timeslotMap = SolutionCallbacks.createTimeslotMap(orm.getTimeslots())  # Mapping from id to Timeslot object.

        # Find out the timeslot of every Lesson and add the Lesson to its Timeslot in the Solution object.
        for lesson in orm.getLessons():
            # tVar is an IntVar of the CpModel that contains the id of the Timeslot the Lesson takes place at.
            for tVar in lesson.timeVars:
                # Add the lesson with its room at the Timeslot the Lesson takes place at.
                sol.addLesson(lesson, roomMap[solver.Value(lesson.roomVar)], timeslotMap[solver.Value(tVar)])

        # Write the solution.
        ExcelWriter.writeTimeTableExcelFile(sol, universityName, departmentName, semesterName, orm)


if __name__ == '__main__':
    """
    Before starting the actual program by calling the main function,
    Python's argparse module is used to parse program arguments,
    print an info and a help text with information about the parameters.
    
    The actual main function is not called if an error occurs while
    parsing the program parameters (e.g. by wrong arguments) or if
    the help parameter -h/--help was specified.
    """

    # Instantiate ArgumentParser with an info text.
    infoText = 'Search for valid timetables. Needs the database file at: ' + ORM.DB_PATH + \
               ' You can change the database path in the file \'ORM.py\'.'
    parser = argparse.ArgumentParser(description=infoText,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # Specify the program parameters.
    parser.add_argument('-o', '--optimize', type=t_or_f, choices=[True, False], default=OPTIMIZE,
                        help='Set if the program should search for an optimal solution. If the opti'
                             'mization is disabled, the search will end with the first solution fou'
                             'nd. Optional constraints will not be evaluated.')

    parser.add_argument('-m', '--max_time', metavar='N', type=int, default=MAX_SEARCH_TIME,
                        help='Set the maximum search time in seconds.')

    parser.add_argument('-p', '--print_solutions', type=int,
                        choices=[PRINT_NONE, PRINT_BEST, PRINT_ALL], default=PRINT_SOLUTIONS,
                        help='Set the option to print solutions during the search. 0 means print no'
                             ' solutions. 1 means print the best/last solution. 2 means print all s'
                             'olutions found during the search.')

    parser.add_argument("-e", "--export", default=EXPORT_TIMETABLE, action='store_true',
                        help="Set this parameter to export the timetable to an Excel file.")

    parser.add_argument('-u', '--university', metavar='NAME', type=str, default=universityName,
                        help='Set the name of the university for the Excel file export. Characters '
                             'used must be compatible with filenames of the operating system and fi'
                             'le system you use.')

    parser.add_argument('-d', '--department', metavar='NAME', type=str, default=departmentName,
                        help='Set the name of the department for the Excel file export. Characters '
                             'used must be compatible with filenames of the operating system and fi'
                             'le system you use.')

    parser.add_argument('-s', '--semester', metavar='NAME', type=str, default=semesterName,
                        help='Set a name of the semester of the timetable for the Excel file export.'
                             ' Characters used must be compatible with filenames of the operating s'
                             'ystem and file system you use.')

    # Parse arguments.
    args = parser.parse_args()
    params = vars(args)
    # print(params)

    # Set the program arguments to used fields.
    OPTIMIZE = params['optimize']
    MAX_SEARCH_TIME = params['max_time']
    PRINT_SOLUTIONS = params['print_solutions']
    EXPORT_TIMETABLE = params['export']
    universityName = params['university']
    departmentName = params['department']
    semesterName = params['semester']

    # Call the main function with the actual program for timetable search.
    ORM.init()
    main()
