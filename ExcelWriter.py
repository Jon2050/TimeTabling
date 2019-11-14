import itertools
from Solution import Solution
import xlsxwriter
from datetime import date
import xlsxwriter.worksheet
import ORM
import Timeslot


# A global dictionary for the XlsxWriter cell formats.
formatMap = dict()


def writeTimeTableExcelFile(timeTableSolution: Solution, universityName, departmentName, semesterName, orm):
    """
    Generates an Excel file with the time table data for students and teachers in german language.
    Using the XlsxWriter library for writing the Excel file.
    """

    # Create the Excel file.
    workbook = xlsxwriter.Workbook("%s_Stundenplan_%s_%s_%s.xlsx" % (date.today().strftime("%Y-%m-%d"), universityName, departmentName, semesterName))

    # Create cell formats and store them in a dictionary.
    global formatMap
    formatMap["simpleBoldFormat"] = workbook.add_format({'bold': True, 'font_size': '11'})
    formatMap["simpleBoldGermanDateFormat"] = workbook.add_format({'num_format': 'dd.mm.yyyy', 'bold': True, 'font_size': '11'})
    formatMap["mainHeaderFormat"] = workbook.add_format({'bold': True, 'font_size': '12', 'font_name': 'Arial', 'valign': 'vcenter', 'bg_color': 'green'})
    formatMap["semesterNameFormat"] = workbook.add_format({'bold': True, 'font_size': '20', 'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter'})
    formatMap["weekdayFormat"] = workbook.add_format({'bold': True, 'font_size': '12', 'font_name': 'Arial', 'align': 'center', 'left': 1, 'right': 1})
    formatMap["timeslotNumberFormat"] = workbook.add_format({'bold': True, 'font_size': '10', 'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter', 'left': 1, 'right': 1})
    formatMap["timeslotTimeFormat"] = workbook.add_format({'font_size': '7', 'font_name': 'Arial', 'align': 'center', 'valign': 'bottom', 'left': 1, 'right': 1})
    formatMap["semesterNumberFormat"] = workbook.add_format({'bold': True, 'font_size': '10', 'font_name': 'Arial', 'valign': 'vcenter', 'bg_color': 'green'})
    formatMap["sgAbbreviationFormat"] = workbook.add_format({'font_size': '9', 'font_name': 'Arial', 'align': 'left'})
    formatMap["lessonContentTopFormat"] = workbook.add_format({'font_size': '9', 'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter', 'left': 1, 'top': 1, 'right': 1})
    formatMap["lessonContentMidFormat"] = workbook.add_format({'font_size': '9', 'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter', 'left': 1, 'right': 1})
    formatMap["lessonContentBottomFormat"] = workbook.add_format({'font_size': '9', 'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter', 'left': 1, 'bottom': 1, 'right': 1})
    formatMap["lessonContentTopFirstFormat"] = workbook.add_format({'font_size': '9', 'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter', 'left': 5, 'top': 1, 'right': 1})
    formatMap["lessonContentMidFirstFormat"] = workbook.add_format({'font_size': '9', 'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter', 'left': 5, 'right': 1})
    formatMap["lessonContentBottomFirstFormat"] = workbook.add_format({'font_size': '9', 'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter', 'left': 5, 'bottom': 1, 'right': 1})
    formatMap["teacherNameFormat"] = workbook.add_format({'bold': True, 'font_size': '11', 'font_name': 'Calibri', 'align': 'left', 'valign': 'vcenter'})
    formatMap["blackBackgroundFormat"] = workbook.add_format({'bg_color': 'black'})
    formatMap["teacherAbbreviationFormat"] = workbook.add_format({'font_size': '9', 'font_name': 'Arial', 'align': 'left', 'valign': 'vcenter', 'top': 1, 'left': 1, 'bottom': 1, 'right': 1})

    # Add a worksheet with the student's timetable to the workbook.
    writeStudentsTimeTable(timeTableSolution, workbook, departmentName, semesterName, orm)
    # Add a worksheet with the teacher's timetable to the workbook.
    writeTeachersTimeTable(timeTableSolution, workbook, departmentName, semesterName, orm)

    # Close the workbook and store it to disk.
    workbook.close()


def writeTeachersTimeTable(timeTableSolution, workbook, departmentName, semesterName, orm):
    """
    Creates a worksheet to the workbook and writes the timetable for all Teachers in the Solution.

    Args:
        timeTableSolution: The timetable Solution
        workbook: The XlsxWriter Workbook.
        departmentName: Name of the university department of the timetable.
        semesterName: Name of the semester, e.g. WS 2018-19
        orm: The ORM file with all objects of the timetable.
    """

    # Create a new worksheet.
    worksheet = workbook.add_worksheet("Lehrende")

    row = 0  # Row counter.
    row = writeHeaderLine(worksheet, departmentName, semesterName, "Lehrende", 18, 18, 8, orm, row)
    worksheet.freeze_panes(row, 0)

    teachers = orm.getTeachers()
    teachers.sort(key=lambda t: t.name)  # The Teacher's should be occur in alphabetical order.
    for teacher in teachers:
        # Add a black row for separating the teachers.
        for column in range(len(orm.getTimeslots()) + 3):
            worksheet.write_blank(row, column, "", formatMap["blackBackgroundFormat"])
        worksheet.set_row(row, 2)
        row += 1
        # Write the Teacher's rows.
        row = writeTeacherRows(worksheet, timeTableSolution, teacher, row, orm)
    # Add a black row after the last teacher.
    for column in range(len(orm.getTimeslots()) + 3):
        worksheet.write_blank(row, column, "", formatMap["blackBackgroundFormat"])
    worksheet.set_row(row, 2)


def writeStudentsTimeTable(timeTableSolution, workbook, departmentName, semesterName, orm):
    """
    Creates a worksheet to the workbook and writes the timetable for all SemesterGroups in the Solution.

    Args:
        timeTableSolution: The timetable Solution
        workbook: The XlsxWriter Workbook.
        departmentName: Name of the university department of the timetable.
        semesterName: Name of the semester, e.g. WS 2018-19
        orm: The ORM file with all objects of the timetable.
    """
    # Create a new worksheet.
    worksheet = workbook.add_worksheet("Studierende")

    row = 0  # Row counter.
    row = writeHeaderLine(worksheet, departmentName, semesterName, "Studenten", 6, 12, 11, orm, row)
    worksheet.freeze_panes(row, 0)

    semesterGroups = orm.getSemesterGroups()
    # Objects needed to be sorted to group them with the itertools groupby.
    semesterGroups.sort(key=lambda sg: sg.study_course)  # Group them by the study course name.
    groups = itertools.groupby(semesterGroups, key=lambda sg: sg.study_course)
    for studyCourse in groups:
        sgList = [x for x in studyCourse[1]]
        # Sort the semesters of the study course by the semester number.
        sgList.sort(key=lambda sg: sg.semester)
        # Write the timetables of the study courses SemesterGroups.
        row = writeStudyCourseRows(worksheet, sgList, timeTableSolution, orm, row)


def writeHeaderLine(worksheet, department, semesterName, subjectName, col1Width, col2Width, col3Width, orm: ORM, row) -> int:
    """
    Writes the worksheet header with creation date and department name.
    Also sets the width of the first three columns.

    Args:
        worksheet: The worksheet to write the header in.
        department: The name of the timetable's department.
        semesterName: The name of the semester.
        subjectName: The subject of the worksheet's timetable. e.g. Teachers or Students.
        col1Width: Width of the first column.
        col2Width: Width of the second column.
        col3Width: Width of the third column.
        orm: The ORM file with all objects of the timetable.
        row: The last row in the worksheet.

    Returns: The next row after the written timetables.
    """
    columnCount = len(orm.getTimeslots()) + 3

    # Write row with the current date.
    worksheet.write(row, 0, "Stand:", formatMap["simpleBoldFormat"])
    worksheet.write_datetime(row, 1, date.today(), formatMap["simpleBoldGermanDateFormat"])
    row += 1

    # Main header line.
    # Add a background to the header row.
    makeBackground(worksheet, columnCount, row, formatMap["mainHeaderFormat"])
    # Set column widths.
    worksheet.set_column(0, 0, col1Width)
    worksheet.set_column(1, 1, col2Width)
    worksheet.set_column(2, 2, col3Width)
    worksheet.set_column(3, columnCount, 7)  # Width of the columns that contain the timetable Lessons.
    # Write main header contents.
    worksheet.write(row, 0, "Stundenplanung", formatMap["mainHeaderFormat"])
    worksheet.write(row, 3, "Fachbereich " + department, formatMap["mainHeaderFormat"])
    worksheet.write(row, 8, subjectName, formatMap["mainHeaderFormat"])
    # Set row height.
    worksheet.set_row(row, 27.75)
    row += 1

    # Weekday and timeslot line.
    row = writeDayAndTimeLine(worksheet, semesterName, orm, row)
    return row


def writeDayAndTimeLine(worksheet, semesterName, orm, row) -> int:
    """
    Write the rows with the timetable's weekdays and Timeslots.

    Args:
        worksheet: The worksheet to add the rows in.
        semesterName: The name of the semester.
        orm: The ORM file with all objects of the timetable.
        row: The current row to write the content in.

    Returns: The next row after the written timetables.
    """
    dayList = orm.getTimeslotsPerDay()
    dayMap = {}
    # Translate weekday names.
    for li in dayList:
        if li[0].weekday == Timeslot.MONDAY:
            dayMap["Montag"] = li
        elif li[0].weekday == Timeslot.TUESDAY:
            dayMap["Dienstag"] = li
        elif li[0].weekday == Timeslot.WEDNESDAY:
            dayMap["Mittwoch"] = li
        elif li[0].weekday == Timeslot.THURSDAY:
            dayMap["Donnerstag"] = li
        elif li[0].weekday == Timeslot.FRIDAY:
            dayMap["Freitag"] = li

    # Merge cells for semester name and writes the semester's name into it.
    worksheet.merge_range(row, 0, row + 2, 2, semesterName, formatMap["semesterNameFormat"])
    column = 3
    worksheet.set_row(row, 26)

    for day, timeslots in dayMap.items():  # Write the Timeslots for each day.
        dayLength = len(timeslots)
        # Merge cells for weekday names and write the weekday's name into it.
        worksheet.merge_range(row, column, row, column + dayLength - 1, day, formatMap["weekdayFormat"])
        for timeslot in timeslots:
            # Write Timeslots numbers and times.
            worksheet.write_string(row + 1, column, "%d." % timeslot.number, formatMap["timeslotNumberFormat"])
            worksheet.write_string(row + 2, column, "%s - %s" % (timeslot.from_time, timeslot.to_time), formatMap["timeslotTimeFormat"])
            column += 1

    return row + 3


def writeStudyCourseRows(worksheet, semesterGroups, timeTableSolution: Solution, orm: ORM, row) -> int:
    """
    Writes the timetables for the given semesterGroups to the excel file in the given worksheet.

    Args:
        worksheet: The worksheet to write the timetables in.
        semesterGroups: The semesterGroups to write the timetables of.
        timeTableSolution: The timetable Solution.
        orm: The ORM file with all objects of the timetable.
        row: The current row in the worksheet to start with the timetables.

    Returns: The next row after the written timetables.
    """

    # Make background for the study course name row.
    makeBackground(worksheet, len(orm.getTimeslots()) + 3, row, formatMap["mainHeaderFormat"])
    worksheet.write_string(row, 0, semesterGroups[0].study_course, formatMap["mainHeaderFormat"])
    worksheet.set_row(row, 27.75)  # Row height.
    row += 1
    # Write timetables of the semester groups of the given study course.
    for semesterGroup in semesterGroups:
        row = writeSemesterGroupRows(worksheet, semesterGroup, timeTableSolution, orm, row)

    return row + 1


def writeSemesterGroupRows(worksheet, semesterGroup, timeTableSolution: Solution, orm: ORM, row) -> int:
    """
    Writes the timetable for the given semestergroup to the excel file in the given worksheet.

    Args:
        worksheet: The worksheet to write the timetables in.
        semesterGroup: The semesterGroup to write the timetable of.
        timeTableSolution: The timetable Solution.
        orm: The ORM file with all objects of the timetable.
        row: The current row in the worksheet to start with the timetables.

    Returns: The next row after the written timetables.
    """

    # Make background for the semester number row.
    makeBackground(worksheet, len(orm.getTimeslots()) + 3, row, formatMap["semesterNumberFormat"])
    # Write semester number.
    worksheet.write_string(row, 0, "%d. Semester" % semesterGroup.semester, formatMap["semesterNumberFormat"])
    worksheet.set_row(row, 14)  # Row height.
    row += 1

    # Split the lessons in the course types and write rows with the lessons for each type.
    courseTypes = list(set(map(lambda l: l.course.type, semesterGroup.getLessons())))
    for courseType in courseTypes:
        row = writeCourseTypeRow(worksheet, courseType, timeTableSolution, semesterGroup, orm, row)

    return row


def writeCourseTypeRow(worksheet, courseType, solution: Solution, semesterGroup, orm, row) -> int:
    """
    Writes the rows for a given course type and the given semester group.

    Args:
        worksheet: The worksheet to write the timetables in.
        courseType: The course type.
        solution: The timetable Solution.
        semesterGroup: The semesterGroup to write the timetable of.
        orm: The ORM file with all objects of the timetable.
        row: The current row in the worksheet to start with the timetables.

    Returns: The next row after the written timetables.
    """
    columnOffset = 3

    lessonsMap = {}  # A dictionary with all Timeslots as keys and the corresponding Lessons as values for Lessons that matches the courseType.
    for timeslot in orm.getTimeslots():
        # Filter for lessons at the current timeslot, the given course type and semester group.
        lessonsAtTimeslot = list(filter(lambda l: l.course.type == courseType and semesterGroup in l.course.semester_groups, solution.getLessonsAtTimeslot(timeslot)))
        if lessonsAtTimeslot:
            lessonsMap[timeslot] = lessonsAtTimeslot

    # Iterate while Lessons are left in the dictionary because there can be more than one Lesson
    # per Timeslot and additional rows are needed for these extra Lessons.
    while lessonsMap:
        # Write SemesterGroup abbreviation and course type to the start of the rows.
        worksheet.write(row, 1, semesterGroup.abbreviation, formatMap["sgAbbreviationFormat"])
        worksheet.write(row + 1, 1, semesterGroup.abbreviation, formatMap["sgAbbreviationFormat"])
        worksheet.write(row + 2, 1, semesterGroup.abbreviation, formatMap["sgAbbreviationFormat"])
        worksheet.write(row + 1, 2, courseType, formatMap["sgAbbreviationFormat"])
        # Make borders around all lesson cells. Write a thicker border on the left side for cells in the row of the first timeslot of a day (...FirstFormat).
        for timeslot in orm.getTimeslots():
            worksheet.write_blank(row, timeslot.id - 1 + columnOffset, None, formatMap["lessonContentTopFormat"] if timeslot.number > 1 else formatMap["lessonContentTopFirstFormat"])
            worksheet.write_blank(row + 1, timeslot.id - 1 + columnOffset, None, formatMap["lessonContentMidFormat"] if timeslot.number > 1 else formatMap["lessonContentMidFirstFormat"])
            worksheet.write_blank(row + 2, timeslot.id - 1 + columnOffset, None, formatMap["lessonContentBottomFormat"] if timeslot.number > 1 else formatMap["lessonContentBottomFirstFormat"])
        # Write Lesson contents into the rows.
        for timeslot, lessonList in dict(lessonsMap).items():  # Iterate over copy of the dictionary to delete keys from it during the iteration.
            lesson = lessonList.pop(0)
            if not lessonList:  # Id list for this timeslot is empty afterwards, remove the list from the dictionary.
                lessonsMap.pop(timeslot)

            # Write Course name.
            worksheet.write_string(row, timeslot.id - 1 + columnOffset, lesson.course.abbreviation, formatMap["lessonContentTopFormat"] if timeslot.number > 1 else formatMap["lessonContentTopFirstFormat"])
            # Write Teacher name.
            worksheet.write_string(row + 1, timeslot.id - 1 + columnOffset, "/".join(map(lambda t: t.abbreviation, lesson.teachers)), formatMap["lessonContentMidFormat"] if timeslot.number > 1 else formatMap["lessonContentMidFirstFormat"])
            # Write Room name.
            worksheet.write_string(row + 2, timeslot.id - 1 + columnOffset, solution.getRoomOfLesson(lesson).name, formatMap["lessonContentBottomFormat"] if timeslot.number > 1 else formatMap["lessonContentBottomFirstFormat"])
        row += 3

    return row


def writeTeacherRows(worksheet, solution, teacher, row, orm) -> int:
    """
    Writes the timetable of the given Teacher to the given worksheet.

    Args:
        worksheet: The worksheet to write the timetables in.
        solution: The timetable Solution.
        teacher: The teacher to write its timetable.
        row: The current row in the worksheet to start with the timetables.
        orm:  The ORM file with all objects of the timetable.

    Returns: The next row after the written timetables.
    """
    startRow = row  # Save the row to start with.

    # Create a dictionary that contains tuples with the Lessons Teachers as keys and the Lessons as list as values.
    teacherGroupMap = {}
    for lesson in teacher.lessons:
        # Sort all Teacher lists the same way, to use them as keys.
        lesson.teachers.sort(key=lambda t: t.abbreviation)
        teacherTuple = tuple(lesson.teachers)
        if teacherTuple not in teacherGroupMap.keys():
            teacherGroupMap[teacherTuple] = []
        teacherGroupMap[teacherTuple].append(lesson)

    keyList = list(teacherGroupMap.keys())
    # Sort the keys by length to get the Teacher Tuple at first that contains only the main Teacher if that Tuple exists.
    keyList.sort(key=lambda k: len(k))
    for key in keyList:
        # Write the row with Lessons with the Teachers in the list (key).
        row = writeTeacherGroupRow(worksheet, solution, teacher, key, teacherGroupMap[key], row, orm)

    # Merge cells in the first two columns and write the Teacher's name into them.
    worksheet.merge_range(startRow, 0, row - 1, 0, teacher.name, formatMap["teacherNameFormat"])
    worksheet.merge_range(startRow, 1, row - 1, 1, teacher.first_name, formatMap["teacherNameFormat"])

    return row


def writeTeacherGroupRow(worksheet, solution, teacher, teacherGroup, lessons, row, orm) -> int:
    """
    Writes the needed timetable rows with all given Lessons.

    Args:
        worksheet: The worksheet to write the timetables in.
        solution: The timetable Solution.
        teacher: The teacher to write its timetable.
        teacherGroup: A group of Teachers that teach all of the given Lessons.
        lessons: The Lessons to write in the row.
        row: The current row in the worksheet to start with the timetables.
        orm:  The ORM file with all objects of the timetable.

    Returns: The next row after the written timetables.
    """
    columnOffset = 3
    lessonsMap = {}  # A dictionary with all Timeslots as keys and the corresponding Lessons as values for Lessons that matches the courseType.
    for timeslot in orm.getTimeslots():
        lessonsAtTimeslot = list(filter(lambda l: l in lessons, solution.getLessonsAtTimeslot(timeslot)))
        if lessonsAtTimeslot:
            lessonsMap[timeslot] = lessonsAtTimeslot

    teacherGroup = [x for x in teacherGroup if x is not teacher]
    teacherGroup = [teacher] + teacherGroup  # Put the Teacher to the front of the list.

    # Iterate while Lessons are left in the dictionary because there can be more than one Lesson per Timeslot and additional rows are needed for these extra Lessons.
    while lessonsMap:
        # Write teacher abbreviation to the start of the rows.
        worksheet.merge_range(row, 2, row + 2, 2, "/".join(list(map(lambda t: t.abbreviation, teacherGroup))), formatMap["teacherAbbreviationFormat"])

        # Make borders around all lesson cells. Write a thicker border on the left side for cells in the row of the first timeslot of a day (...FirstFormat).
        for timeslot in orm.getTimeslots():
            worksheet.write_blank(row, timeslot.id - 1 + columnOffset, None, formatMap["lessonContentTopFormat"] if timeslot.number > 1 else formatMap["lessonContentTopFirstFormat"])
            worksheet.write_blank(row + 1, timeslot.id - 1 + columnOffset, None, formatMap["lessonContentMidFormat"] if timeslot.number > 1 else formatMap["lessonContentMidFirstFormat"])
            worksheet.write_blank(row + 2, timeslot.id - 1 + columnOffset, None, formatMap["lessonContentBottomFormat"] if timeslot.number > 1 else formatMap["lessonContentBottomFirstFormat"])
        # Write Lesson contents into the rows.
        for timeslot, lessonList in dict(lessonsMap).items():  # Iterate over copy of the dictionary to delete keys from it during the iteration.
            lesson = lessonList.pop(0)
            if not lessonList:  # Id list for this timeslot is empty afterwards, remove the list from the dictionary.
                lessonsMap.pop(timeslot)

            # Write Course name.
            worksheet.write_string(row, timeslot.id - 1 + columnOffset, lesson.course.abbreviation, formatMap["lessonContentTopFormat"] if timeslot.number > 1 else formatMap["lessonContentTopFirstFormat"])
            # Write Teacher name.
            worksheet.write_string(row + 1, timeslot.id - 1 + columnOffset, "/".join(map(lambda sg: sg.abbreviation, lesson.course.semester_groups)), formatMap["lessonContentMidFormat"] if timeslot.number > 1 else formatMap["lessonContentMidFirstFormat"])
            # Write Room name.
            worksheet.write_string(row + 2, timeslot.id - 1 + columnOffset, solution.getRoomOfLesson(lesson).name, formatMap["lessonContentBottomFormat"] if timeslot.number > 1 else formatMap["lessonContentBottomFirstFormat"])
        row += 3

    return row


def makeBackground(worksheet, columns, row, format, shift=0):
    """
    Apply the given format to the cells of the given row. Cell contents will be overridden.

    Args:
        worksheet: The worksheet to write at.
        columns: The number of columns to apply the format to.
        row: The row to apply the format in.
        format: The format.
        shift: A shift at the start of the row.

    Returns: The next row after the written timetables.
    """
    for column in range(shift, columns):
        worksheet.write(row, column, None, format)
