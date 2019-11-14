import random
import typing

from sqlalchemy import create_engine, or_, orm
from sqlalchemy.orm import sessionmaker, Session

import ORM
from Course import Course
from Lesson import Lesson
from Room import Room
from SemesterGroup import SemesterGroup
from Teacher import Teacher
from Timeslot import Timeslot, MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY


def dropAll(session: Session):
    """
    Drop all data and reset primary keys.
    Only the Timeslot entries are retained.

    Args:
        session: SQLAlchemy Session object.
    """

    # Clear the object tables:
    session.query(Teacher).delete()
    session.query(Room).delete()
    session.query(Course).delete()
    session.query(Lesson).delete()
    session.query(SemesterGroup).delete()
    session.commit()

    # Clearing the object tables should cascade and delete all entries in the
    # relationship association tables but SQLAlchemy seems to delete without this cascade.
    # So clear association tables manually:
    session.execute("delete from course__room;")
    session.execute("delete from course__semester_group;")
    session.execute("delete from lesson__teacher;")
    session.execute("delete from not_available_timeslots__room;")
    session.execute("delete from not_available_timeslots__teacher;")
    session.execute("delete from available_timeslots__lesson;")
    session.execute("delete from lessons_same_time;")
    session.execute("delete from lessons_consecutive;")

    # Delete primary key sequences:
    session.execute("delete from sqlite_sequence where name=\'teacher\';")
    session.execute("delete from sqlite_sequence where name=\'room\';")
    session.execute("delete from sqlite_sequence where name=\'course\';")
    session.execute("delete from sqlite_sequence where name=\'lesson\';")
    session.execute("delete from sqlite_sequence where name=\'semester_group\';")


def createCourse(courseName, abbreviation, courseType, lessonLengthList, teacherList, semesterGroupList, roomList, onlyForenoon=False, isLecture=False, allInOneBlock=False, onePerDayPerTeacher=False, wholeSemesterGroup=True) -> Course:
    """
    Creates a course with lessons. Adds room, teacher and semester group relationships.

    Args:
        courseName: str: Name of the course.
        abbreviation: str: Abbreviation of the course.
        courseType: str: Type of the course. E.g. Lecture, Practical, Practice, Project.
        lessonLengthList: [int]: List with Lesson lengths. Add one element for each lesson of the course.
                                 E.g. [1,1,1] for a course with 3 Lessons.
        teacherList: [Teacher] or [[Teacher]]: List with Teachers for all Lessons or list with lists for each single Lesson.
                                               E.g.: [TeacherA] for TeacherA at all Lessons or [[TeacherA], [TeacherB], [TeacherA, TeacherB]]
                                               for different teachers on each lesson.
        semesterGroupList: [SemesterGroup]: List with participating semester groups.
        roomList: [Room]: List with available rooms for the course.
        onlyForenoon: Set if the cours should only take place at forenoon.
        isLecture: Set if the course is a lecture.
        allInOneBlock: Set if all lessons of the course should take place as one block.
        onePerDayPerTeacher: Set if this is a OnePerDayPerTeacher course.
        wholeSemesterGroup: Set if whole semester groups participate on each lesson.

    Returns: The created course object.
    """
    newCourse = Course(name=courseName,
                       abbreviation=abbreviation,
                       type=courseType,
                       only_forenoon=onlyForenoon,
                       is_lecture=isLecture,
                       all_in_one_block=allInOneBlock,
                       one_per_day_per_teacher=onePerDayPerTeacher)

    lessonList = []
    for i in range(0, len(lessonLengthList)):
        lessonList.append(Lesson(timeslot_size=lessonLengthList[i], whole_semester_group=wholeSemesterGroup,
                                 teachers=teacherList if type(teacherList[0]) is Teacher else teacherList[i]))

    newCourse.lessons.extend(lessonList)
    newCourse.possible_rooms.extend(roomList)
    newCourse.semester_groups.extend(semesterGroupList)
    return newCourse


def timeslotByID(session, ID) -> Timeslot:
    """
    Args:
        session: SQLAlchemy Session object.
        ID: ID of a timeslot.

    Returns: The timeslot with the given id.
    """
    return session.query(Timeslot).get(ID)


def timeslotsByID(session, *ID) -> typing.List[Timeslot]:
    """
    Args:
        session: SQLAlchemy Session object.
        ID: Multiple IDs of timeslot.

    Returns: All timeslots with the given IDs.
    """
    return [timeslotByID(session, x) for x in ID]


def generateBigDataset(session: Session):
    """
    Generates a timetable and adds it to the database.

    The timetable is very roughly based on the timetable of the faculty E+I of the TH-Lübeck,
    in a winter semester. All details like lesson lengths, number of lessons per course, teachers
    of the courses and much more are fictitious and the generated timetable is a bit smaller.

    Timetable will contain:
    Teachers:         27
    Rooms:            14
    SemesterGroups:   14
    Courses:          61
    Lessons:         135
    Lesson Hours:    151

    Args:
        session: SQLAlchemy Session object.
    """

    dropAll(session)

    # Geenrate teachers.
    teacher1 = Teacher(name="T1", first_name="TF_1", abbreviation="t1", study_day_1=MONDAY, study_day_2=FRIDAY, max_lessons_per_day=4, max_lectures_as_block=2)
    teacher2 = Teacher(name="T2", first_name="TF_2", abbreviation="t2", study_day_1=MONDAY, study_day_2=FRIDAY)
    teacher3 = Teacher(name="T3", first_name="TF_3", abbreviation="t3", study_day_1=TUESDAY, study_day_2=WEDNESDAY, max_lectures_as_block=2, avoid_free_day_gaps=True)
    teacher4 = Teacher(name="T4", first_name="TF_4", abbreviation="t4", study_day_1=FRIDAY, study_day_2=FRIDAY)
    teacher5 = Teacher(name="T5", first_name="TF_5", abbreviation="t5", study_day_1=FRIDAY, study_day_2=THURSDAY, max_lectures_per_day=3)
    teacher6 = Teacher(name="T6", first_name="TF_6", abbreviation="t6", study_day_1=TUESDAY, study_day_2=MONDAY, max_lessons_per_day=4, max_lectures_per_day=3, max_lectures_as_block=2)
    teacher7 = Teacher(name="T7", first_name="TF_7", abbreviation="t7", study_day_1=MONDAY, study_day_2=THURSDAY)
    teacher8 = Teacher(name="T8", first_name="TF_8", abbreviation="t8", study_day_1=MONDAY, study_day_2=WEDNESDAY, max_lectures_as_block=3, avoid_free_day_gaps=True)
    teacher9 = Teacher(name="T9", first_name="TF_9", abbreviation="t9", study_day_1=TUESDAY, study_day_2=TUESDAY, max_lectures_as_block=1)
    teacher10 = Teacher(name="T10", first_name="TF_10", abbreviation="t10", study_day_1=MONDAY, study_day_2=MONDAY)
    teacher11 = Teacher(name="T11", first_name="TF_11", abbreviation="t11", study_day_1=WEDNESDAY, study_day_2=THURSDAY)
    teacher12 = Teacher(name="T12", first_name="TF_12", abbreviation="t12", study_day_1=None, study_day_2=None, max_lessons_per_day=4, avoid_free_day_gaps=True)
    teacher13 = Teacher(name="T13", first_name="TF_13", abbreviation="t13", study_day_1=None, study_day_2=None, max_lectures_per_day=4)
    teacher14 = Teacher(name="T14", first_name="TF_14", abbreviation="t14", study_day_1=None, study_day_2=None, max_lectures_as_block=3)
    teacher15 = Teacher(name="T15", first_name="TF_15", abbreviation="t15", study_day_1=None, study_day_2=None, max_lessons_per_day=4, max_lectures_per_day=3, max_lectures_as_block=2, avoid_free_day_gaps=True)
    teacher16 = Teacher(name="T16", first_name="TF_16", abbreviation="t16", study_day_1=None, study_day_2=None, avoid_free_day_gaps=True)
    teacher17 = Teacher(name="T17", first_name="TF_17", abbreviation="t17", study_day_1=None, study_day_2=None)
    teacher18 = Teacher(name="T18", first_name="TF_18", abbreviation="t18", study_day_1=None, study_day_2=None)
    teacher19 = Teacher(name="T19", first_name="TF_19", abbreviation="t19", study_day_1=None, study_day_2=None)
    teacher20 = Teacher(name="T20", first_name="TF_20", abbreviation="t20", study_day_1=None, study_day_2=None)
    teacher21 = Teacher(name="T21", first_name="TF_21", abbreviation="t21", study_day_1=None, study_day_2=None)
    teacher22 = Teacher(name="T22", first_name="TF_22", abbreviation="t22", study_day_1=None, study_day_2=None)
    teacher23 = Teacher(name="T23", first_name="TF_23", abbreviation="t23", study_day_1=None, study_day_2=None)
    teacher24 = Teacher(name="T24", first_name="TF_24", abbreviation="t24", study_day_1=None, study_day_2=None)
    teacher25 = Teacher(name="T25", first_name="TF_25", abbreviation="t25", study_day_1=THURSDAY, study_day_2=FRIDAY)
    teacher26 = Teacher(name="T26", first_name="TF_26", abbreviation="t26", study_day_1=TUESDAY, study_day_2=WEDNESDAY)
    teacher27 = Teacher(name="T27", first_name="TF_27", abbreviation="t27", study_day_1=MONDAY, study_day_2=FRIDAY)
    s = session
    teacher1.not_available_timeslots.extend([timeslotByID(s, 1), timeslotByID(s, 2)])
    teacher5.not_available_timeslots.extend([timeslotByID(s, 1), timeslotByID(s, 8), timeslotByID(s, 19)])
    teacher11.not_available_timeslots.extend([timeslotByID(s, 4), timeslotByID(s, 29), timeslotByID(s, 30)])
    teacher12.not_available_timeslots.extend([timeslotByID(s, 28), timeslotByID(s, 29), timeslotByID(s, 30)])
    teacher16.not_available_timeslots.extend([timeslotByID(s, 10), timeslotByID(s, 11)])

    session.add_all((teacher1, teacher2, teacher3, teacher4, teacher5, teacher6, teacher7, teacher8,
                     teacher9, teacher10, teacher11, teacher12, teacher13, teacher14, teacher15,
                     teacher16, teacher17, teacher18, teacher19, teacher20, teacher21, teacher22,
                     teacher23, teacher24, teacher25, teacher26, teacher27))

    # Create some rooms.
    room1 = Room(name="1-1.1")
    room2 = Room(name="2-2.2")
    room3 = Room(name="3-3.3")
    room4 = Room(name="4-4.4")
    room5 = Room(name="5-5.5")
    room6 = Room(name="6-6.6")
    room7 = Room(name="7-7.7")
    room8 = Room(name="8-8.8")
    room9 = Room(name="9-9.9")
    room10 = Room(name="10-10.10")
    room11 = Room(name="11-11.11")
    room12 = Room(name="12-12.12")
    room13 = Room(name="13-13.13")
    room14 = Room(name="14-14.14")

    room3.not_available_timeslots.extend([timeslotByID(s, 4), timeslotByID(s, 5)])
    room6.not_available_timeslots.extend([timeslotByID(s, 8)])
    room8.not_available_timeslots.extend([timeslotByID(s, 19)])
    room11.not_available_timeslots.extend([timeslotByID(s, 11), timeslotByID(s, 12)])
    room12.not_available_timeslots.extend([timeslotByID(s, 7)])

    session.add_all((room1, room2, room3, room4, room5, room6, room7, room8, room9, room10, room11, room12, room13, room14))

    # Create some semester groups.
    semester_group1 = SemesterGroup(study_course="Informatik/Softwaretechnik", semester=1)
    semester_group2 = SemesterGroup(study_course="Informatik/Softwaretechnik", semester=3)
    semester_group3 = SemesterGroup(study_course="Informatik/Softwaretechnik", semester=5)
    semester_group4 = SemesterGroup(study_course="ET: Energiesysteme und Automation", semester=1, max_lessons_per_day=6)
    semester_group5 = SemesterGroup(study_course="ET: Energiesysteme und Automation", semester=3, max_lessons_per_day=6)
    semester_group6 = SemesterGroup(study_course="ET: Energiesysteme und Automation", semester=5)
    semester_group7 = SemesterGroup(study_course="ET: Kommunikationssysteme", semester=1, max_lessons_per_day=6)
    semester_group8 = SemesterGroup(study_course="ET: Kommunikationssysteme", semester=3, max_lessons_per_day=6)
    semester_group9 = SemesterGroup(study_course="ET: Kommunikationssysteme", semester=5)
    semester_group10 = SemesterGroup(study_course="Informationstechnologie und Design", semester=1, max_lessons_per_day=4)
    semester_group11 = SemesterGroup(study_course="Informationstechnologie und Design", semester=3)
    semester_group12 = SemesterGroup(study_course="Informationstechnologie und Design", semester=5, free_day="WE")
    semester_group13 = SemesterGroup(study_course="Angewandte Informationstechnik", semester=1)
    semester_group14 = SemesterGroup(study_course="Angewandte Informationstechnik", semester=3, free_day="TU")

    session.add_all((semester_group1, semester_group2, semester_group3, semester_group4,
                     semester_group5, semester_group6, semester_group7, semester_group8,
                     semester_group9, semester_group10, semester_group11, semester_group12,
                     semester_group13, semester_group14))

    # Create courses for the semester groups.

    # INF/SWT Courses
    course1 = Course(abbreviation="Inf I", name="Informatik I", type="Vorlesung", only_forenoon=True, is_lecture=True)
    course2 = Course(abbreviation="MA I", name="Mathe I", type="Vorlesung", only_forenoon=True, is_lecture=True)
    course3 = Course(abbreviation="MA I Üb", name="Mathe I Übung", type="Übung")
    course4 = Course(abbreviation="Prog I", name="Programmieren I", type="Vorlesung", is_lecture=True, all_in_one_block=True)
    course5 = Course(abbreviation="Prog I Pr", name="Programmieren I Praktikum", type="Praktika")
    course6 = Course(abbreviation="DB", name="Datenbanken", type="Vorlesung", only_forenoon=True, is_lecture=True)
    course7 = Course(abbreviation="SWT I", name="Softwaretechnik I", type="Vorlesung", is_lecture=True)
    course8 = Course(abbreviation="SWT I Pr", name="Softwaretechnik I Praktikum", type="Praktika")
    course9 = Course(abbreviation="RN", name="Rechnernetze", type="Vorlesung", is_lecture=True)
    course10 = Course(abbreviation="RN Pr", name="Rechnernetze Praktikum", type="Praktika", one_per_day_per_teacher=True)
    course11 = Course(abbreviation="BS", name="Betriebssysteme", type="Vorlesung", is_lecture=True)
    course12 = Course(abbreviation="BS Pr", name="Betriebssysteme Praktikum", type="Praktika")
    course13 = Course(abbreviation="VS", name="Verteilte Systeme", type="Vorlesung", only_forenoon=True, is_lecture=True)
    course14 = Course(abbreviation="Übs", name="Formale Sprachen und Übersetzertechniken", type="Vorlesung", is_lecture=True)
    course61 = Course(abbreviation="Übs Pr", name="Formale Sprachen und Übersetzertechniken Praktikum", type="Praktika", all_in_one_block=True)
    course15 = Course(abbreviation="IS", name="Intelligente Systeme", type="Vorlesung", is_lecture=True)
    course16 = Course(abbreviation="IS Pr", name="Intelligente Systeme Praktikum", type="Praktika", one_per_day_per_teacher=False, all_in_one_block=True)

    session.add_all((course1, course2, course3, course4, course5, course6, course7, course8, course9, course10, course11, course12, course13, course14, course15, course16, course61))

    course1.semester_groups.append(semester_group1)
    course2.semester_groups.append(semester_group1)
    course3.semester_groups.append(semester_group1)
    course4.semester_groups.append(semester_group1)
    course5.semester_groups.append(semester_group1)
    course6.semester_groups.append(semester_group1)
    course7.semester_groups.append(semester_group2)
    course8.semester_groups.append(semester_group2)
    course9.semester_groups.append(semester_group2)
    course10.semester_groups.append(semester_group2)
    course11.semester_groups.append(semester_group2)
    course12.semester_groups.append(semester_group2)
    course13.semester_groups.append(semester_group2)
    course14.semester_groups.append(semester_group3)
    course15.semester_groups.append(semester_group3)
    course16.semester_groups.append(semester_group3)
    course61.semester_groups.append(semester_group3)

    course1.possible_rooms.append(room1)
    course2.possible_rooms.append(room1)
    course3.possible_rooms.append(room4)
    course3.possible_rooms.append(room5)
    course3.possible_rooms.append(room6)
    course4.possible_rooms.append(room1)
    course5.possible_rooms.append(room6)
    course5.possible_rooms.append(room7)
    course5.possible_rooms.append(room8)
    course6.possible_rooms.append(room1)
    course7.possible_rooms.append(room1)
    course7.possible_rooms.append(room2)
    course8.possible_rooms.append(room5)
    course8.possible_rooms.append(room5)
    course8.possible_rooms.append(room5)
    course9.possible_rooms.append(room1)
    course9.possible_rooms.append(room2)
    course10.possible_rooms.append(room1)
    course10.possible_rooms.append(room12)
    course10.possible_rooms.append(room13)
    course11.possible_rooms.append(room1)
    course11.possible_rooms.append(room2)
    course12.possible_rooms.append(room5)
    course12.possible_rooms.append(room6)
    course12.possible_rooms.append(room7)
    course13.possible_rooms.append(room1)
    course14.possible_rooms.append(room1)
    course14.possible_rooms.append(room2)
    course15.possible_rooms.append(room1)
    course15.possible_rooms.append(room2)
    course16.possible_rooms.append(room5)
    course16.possible_rooms.append(room6)
    course61.possible_rooms.append(room5)
    course61.possible_rooms.append(room6)

    lesson1_1 = Lesson()
    lesson1_2 = Lesson()
    lesson1_3 = Lesson()
    lesson2_1 = Lesson()
    lesson2_2 = Lesson()
    lesson2_3 = Lesson()
    lesson3_1 = Lesson(whole_semester_group=False)
    lesson3_2 = Lesson(whole_semester_group=False)
    lesson3_3 = Lesson(whole_semester_group=False)
    lesson4_1 = Lesson()
    lesson4_2 = Lesson()
    lesson5_1 = Lesson(whole_semester_group=False)
    lesson5_2 = Lesson(whole_semester_group=False)
    lesson5_3 = Lesson(whole_semester_group=False)
    lesson5_4 = Lesson(whole_semester_group=False)
    lesson6_1 = Lesson()
    lesson6_2 = Lesson()
    lesson7_1 = Lesson()
    lesson7_2 = Lesson()
    lesson8_1 = Lesson(whole_semester_group=False)
    lesson8_2 = Lesson(whole_semester_group=False)
    lesson8_3 = Lesson(whole_semester_group=False)
    lesson8_4 = Lesson(whole_semester_group=False)
    lesson8_5 = Lesson(whole_semester_group=False)
    lesson9_1 = Lesson()
    lesson10_1 = Lesson(timeslot_size=2)
    lesson11_1 = Lesson()
    lesson11_2 = Lesson()
    lesson12_1 = Lesson(whole_semester_group=False)
    lesson12_2 = Lesson(whole_semester_group=False)
    lesson12_3 = Lesson(whole_semester_group=False)
    lesson13_1 = Lesson()
    lesson13_2 = Lesson()
    lesson14_1 = Lesson()
    lesson14_2 = Lesson()
    lesson61_1 = Lesson()
    lesson61_2 = Lesson()
    lesson61_3 = Lesson()
    lesson61_4 = Lesson(timeslot_size=2)
    lesson15_1 = Lesson()
    lesson15_2 = Lesson()
    lesson16_1 = Lesson()
    lesson16_2 = Lesson()
    lesson16_3 = Lesson()

    lesson1_1.teachers.append(teacher1)
    lesson1_2.teachers.append(teacher1)
    lesson1_3.teachers.append(teacher1)
    lesson2_1.teachers.append(teacher2)
    lesson2_2.teachers.append(teacher2)
    lesson2_3.teachers.append(teacher2)
    lesson3_1.teachers.append(teacher2)
    lesson3_2.teachers.append(teacher2)
    lesson3_3.teachers.append(teacher2)
    lesson4_1.teachers.append(teacher3)
    lesson4_2.teachers.append(teacher3)
    lesson5_1.teachers.append(teacher4)
    lesson5_2.teachers.append(teacher4)
    lesson5_3.teachers.append(teacher5)
    lesson5_4.teachers.append(teacher5)
    lesson6_1.teachers.append(teacher5)
    lesson6_2.teachers.append(teacher4)
    lesson7_1.teachers.append(teacher3)
    lesson7_2.teachers.append(teacher7)
    lesson8_1.teachers.append(teacher3)
    lesson8_2.teachers.append(teacher3)
    lesson8_3.teachers.append(teacher4)
    lesson8_4.teachers.append(teacher4)
    lesson8_5.teachers.append(teacher6)
    lesson9_1.teachers.append(teacher2)
    lesson10_1.teachers.append(teacher1)
    lesson11_1.teachers.append(teacher1)
    lesson11_2.teachers.append(teacher3)
    lesson12_1.teachers.append(teacher1)
    lesson12_2.teachers.append(teacher4)
    lesson12_3.teachers.append(teacher5)
    lesson13_1.teachers.append(teacher7)
    lesson13_2.teachers.append(teacher7)
    lesson14_1.teachers.append(teacher17)
    lesson14_2.teachers.append(teacher17)
    lesson61_1.teachers.append(teacher6)
    lesson61_2.teachers.append(teacher5)
    lesson61_3.teachers.append(teacher5)
    lesson61_4.teachers.append(teacher17)
    lesson15_1.teachers.append(teacher3)
    lesson15_1.teachers.append(teacher9)
    lesson15_2.teachers.append(teacher3)
    lesson15_2.teachers.append(teacher9)
    lesson16_1.teachers.append(teacher1)
    lesson16_2.teachers.append(teacher2)
    lesson16_3.teachers.append(teacher3)

    course1.lessons.extend([lesson1_1, lesson1_2, lesson1_3])
    course2.lessons.extend([lesson2_1, lesson2_2, lesson2_3])
    course3.lessons.extend([lesson3_1, lesson3_2, lesson3_3])
    course4.lessons.extend([lesson4_1, lesson4_2])
    course5.lessons.extend([lesson5_1, lesson5_2, lesson5_3, lesson5_4])
    course6.lessons.extend([lesson6_1, lesson6_2])
    course7.lessons.extend([lesson7_1, lesson7_2])
    course8.lessons.extend([lesson8_1, lesson8_2, lesson8_3, lesson8_4, lesson8_5])
    course9.lessons.extend([lesson9_1])
    course10.lessons.extend([lesson10_1])
    course11.lessons.extend([lesson11_1, lesson11_2])
    course12.lessons.extend([lesson12_1, lesson12_2, lesson12_3])
    course13.lessons.extend([lesson13_1, lesson13_2])
    course14.lessons.extend([lesson14_1, lesson14_2])
    course15.lessons.extend([lesson15_1, lesson15_2])
    course16.lessons.extend([lesson16_1, lesson16_2, lesson16_3])
    course61.lessons.extend([lesson61_1, lesson61_2, lesson61_3, lesson61_4])

    # ET: ESA Courses
    course17 = Course(abbreviation="Phy I", name="Physik I", type="Vorlesung", only_forenoon=True, is_lecture=True)
    course18 = Course(abbreviation="GE I", name="Grundlagen der Elektrotechnik I", type="Vorlesung", only_forenoon=True, is_lecture=True)
    course19 = Course(abbreviation="GE I Pr", name="Grundlagen der Elektrotechnik I Praktikum", type="Praktika")
    course20 = Course(abbreviation="Prog I", name="Programmieren I", type="Vorlesung", is_lecture=True)
    course21 = Course(abbreviation="Prog I Pr", name="Programmieren I Praktikum", type="Praktika")
    course22 = Course(abbreviation="PrM", name="Projekt- und Selbstmanagement", type="Vorlesung", is_lecture=True)
    course23 = Course(abbreviation="Sig", name="Signale und Systeme", type="Vorlesung", is_lecture=True)
    course24 = Course(abbreviation="Mess", name="Messtechnik und Sensorik", type="Vorlesung")
    course25 = Course(abbreviation="MPT II", name="Mikroprozesortechnik II", type="Vorlesung", is_lecture=True)
    course26 = Course(abbreviation="BE", name="Bauelemente und analoge Elektronik", type="Vorlesung", is_lecture=True)
    course27 = Course(abbreviation="BE Pr", name="Bauelemente und analoge Elektronik Praktikum", type="Praktika", all_in_one_block=True)
    course28 = Course(abbreviation="GE III", name="Grundlagen der Elektrotechnik III", type="Vorlesung", is_lecture=True)
    course29 = Course(abbreviation="EA", name="Elektrische Antriebstechnik", type="Vorlesung")
    course30 = Course(abbreviation="RegE", name="Regenerative Energien", type="Vorlesung", is_lecture=True)
    course31 = Course(abbreviation="FBT", name="Feldbustechnologien", type="Vorlesung", is_lecture=True)
    course32 = Course(abbreviation="ESys", name="Eingebettete Systeme", type="Vorlesung", one_per_day_per_teacher=True, all_in_one_block=True)

    session.add_all((course17, course18, course19, course20, course21, course22, course23, course24, course25, course26, course27, course28, course29, course30, course31, course32))

    course2.semester_groups.append(semester_group4)
    course3.semester_groups.append(semester_group4)
    course17.semester_groups.append(semester_group4)
    course18.semester_groups.append(semester_group4)
    course19.semester_groups.append(semester_group4)
    course20.semester_groups.append(semester_group4)
    course21.semester_groups.append(semester_group4)
    course22.semester_groups.append(semester_group4)
    course23.semester_groups.append(semester_group5)
    course24.semester_groups.append(semester_group5)
    course25.semester_groups.append(semester_group5)
    course26.semester_groups.append(semester_group5)
    course27.semester_groups.append(semester_group5)
    course28.semester_groups.append(semester_group5)
    course29.semester_groups.append(semester_group6)
    course30.semester_groups.append(semester_group6)
    course31.semester_groups.append(semester_group6)
    course32.semester_groups.append(semester_group6)

    course17.possible_rooms.append(room1)
    course18.possible_rooms.append(room1)
    course19.possible_rooms.append(room8)
    course19.possible_rooms.append(room9)
    course19.possible_rooms.append(room10)
    course20.possible_rooms.append(room2)
    course20.possible_rooms.append(room3)
    course21.possible_rooms.append(room6)
    course21.possible_rooms.append(room5)
    course22.possible_rooms.append(room11)
    course22.possible_rooms.append(room10)
    course23.possible_rooms.append(room1)
    course23.possible_rooms.append(room3)
    course24.possible_rooms.append(room1)
    course25.possible_rooms.append(room1)
    course25.possible_rooms.append(room2)
    course26.possible_rooms.append(room2)
    course26.possible_rooms.append(room3)
    course27.possible_rooms.append(room7)
    course27.possible_rooms.append(room8)
    course27.possible_rooms.append(room9)
    course28.possible_rooms.append(room2)
    course28.possible_rooms.append(room3)
    course29.possible_rooms.append(room3)
    course29.possible_rooms.append(room2)
    course30.possible_rooms.append(room2)
    course30.possible_rooms.append(room3)
    course31.possible_rooms.append(room3)
    course32.possible_rooms.append(room2)

    lesson17_1 = Lesson()
    lesson17_2 = Lesson()
    lesson18_1 = Lesson()
    lesson18_2 = Lesson()
    lesson19_1 = Lesson(whole_semester_group=False)
    lesson19_2 = Lesson(whole_semester_group=False)
    lesson19_3 = Lesson(whole_semester_group=False)
    lesson20_1 = Lesson()
    lesson20_2 = Lesson(timeslot_size=2)
    lesson21_1 = Lesson(whole_semester_group=False)
    lesson21_2 = Lesson(whole_semester_group=False)
    lesson21_3 = Lesson(whole_semester_group=False)
    lesson22_1 = Lesson()
    lesson22_2 = Lesson()
    lesson22_3 = Lesson()
    lesson23_1 = Lesson()
    lesson23_2 = Lesson()
    lesson24_1 = Lesson(timeslot_size=2)
    lesson24_2 = Lesson(timeslot_size=2)
    lesson24_3 = Lesson(timeslot_size=2)
    lesson25_1 = Lesson()
    lesson25_2 = Lesson()
    lesson25_3 = Lesson()
    lesson26_1 = Lesson()
    lesson26_2 = Lesson()
    lesson27_1 = Lesson(whole_semester_group=False, timeslot_size=2)
    lesson27_2 = Lesson(whole_semester_group=False, timeslot_size=2)
    lesson27_3 = Lesson(whole_semester_group=False, timeslot_size=2)
    lesson28_1 = Lesson()
    lesson28_2 = Lesson()
    lesson29_1 = Lesson()
    lesson29_2 = Lesson()
    lesson29_3 = Lesson()
    lesson30_1 = Lesson(timeslot_size=2)
    lesson31_1 = Lesson()
    lesson31_2 = Lesson()
    lesson32_1 = Lesson()
    lesson32_2 = Lesson()

    lesson17_1.teachers.append(teacher6)
    lesson17_2.teachers.append(teacher6)
    lesson18_1.teachers.append(teacher17)
    lesson18_2.teachers.append(teacher17)
    lesson19_1.teachers.append(teacher9)
    lesson19_2.teachers.append(teacher9)
    lesson19_3.teachers.append(teacher10)
    lesson20_1.teachers.append(teacher10)
    lesson20_2.teachers.append(teacher10)
    lesson21_1.teachers.append(teacher11)
    lesson21_2.teachers.append(teacher12)
    lesson21_3.teachers.append(teacher13)
    lesson22_1.teachers.append(teacher9)
    lesson22_2.teachers.append(teacher9)
    lesson22_3.teachers.append(teacher9)
    lesson23_1.teachers.append(teacher18)
    lesson23_2.teachers.append(teacher18)
    lesson24_1.teachers.append(teacher18)
    lesson24_2.teachers.append(teacher12)
    lesson24_3.teachers.append(teacher14)
    lesson25_1.teachers.append(teacher14)
    lesson25_2.teachers.append(teacher13)
    lesson25_3.teachers.append(teacher12)
    lesson26_1.teachers.append(teacher18)
    lesson26_2.teachers.append(teacher12)
    lesson27_1.teachers.append(teacher10)
    lesson27_2.teachers.append(teacher8)
    lesson27_3.teachers.append(teacher8)
    lesson28_1.teachers.append(teacher11)
    lesson28_2.teachers.append(teacher11)
    lesson29_1.teachers.append(teacher7)
    lesson29_2.teachers.append(teacher8)
    lesson29_3.teachers.append(teacher9)
    lesson30_1.teachers.append(teacher5)
    lesson31_1.teachers.append(teacher3)
    lesson31_2.teachers.append(teacher3)
    lesson32_1.teachers.append(teacher1)
    lesson32_2.teachers.append(teacher1)

    course17.lessons.extend([lesson17_1, lesson17_2])
    course18.lessons.extend([lesson18_1, lesson18_2])
    course19.lessons.extend([lesson19_1, lesson19_2, lesson19_3])
    course20.lessons.extend([lesson20_1, lesson20_2])
    course21.lessons.extend([lesson21_1, lesson21_2, lesson21_3])
    course22.lessons.extend([lesson22_1, lesson22_2, lesson22_3])
    course23.lessons.extend([lesson23_1, lesson23_2])
    course24.lessons.extend([lesson24_1, lesson24_2, lesson24_3])
    course25.lessons.extend([lesson25_1, lesson25_2, lesson25_3])
    course26.lessons.extend([lesson26_1, lesson26_2])
    course27.lessons.extend([lesson27_1, lesson27_2, lesson27_3])
    course28.lessons.extend([lesson28_1, lesson28_2])
    course29.lessons.extend([lesson29_1, lesson29_2, lesson29_3])
    course30.lessons.extend([lesson30_1])
    course31.lessons.extend([lesson31_1, lesson31_2])
    course32.lessons.extend([lesson32_1, lesson32_2])

    # ET: EKS Courses
    course33 = Course(abbreviation="HintrS", name="Hochintegrierte Schaltungen", type="Vorlesung", is_lecture=True)
    course34 = Course(abbreviation="DÜ", name="Digitale Übertragungstechnik", type="Vorlesung", all_in_one_block=True)
    course35 = Course(abbreviation="HWE", name="Hardwareentwurf", type="Vorlesung", is_lecture=True)
    course36 = Course(abbreviation="KN", name="Kommunikationsnetze", type="Vorlesung", one_per_day_per_teacher=True)

    session.add_all((course33, course34, course35, course36))

    course2.semester_groups.append(semester_group7)
    course3.semester_groups.append(semester_group7)
    course17.semester_groups.append(semester_group7)
    course18.semester_groups.append(semester_group7)
    course19.semester_groups.append(semester_group7)
    course20.semester_groups.append(semester_group7)
    course21.semester_groups.append(semester_group7)
    course22.semester_groups.append(semester_group7)
    course23.semester_groups.append(semester_group8)
    course24.semester_groups.append(semester_group8)
    course25.semester_groups.append(semester_group8)
    course26.semester_groups.append(semester_group8)
    course27.semester_groups.append(semester_group8)
    course28.semester_groups.append(semester_group8)
    course33.semester_groups.append(semester_group9)
    course34.semester_groups.append(semester_group9)
    course35.semester_groups.append(semester_group9)
    course36.semester_groups.append(semester_group9)

    course33.possible_rooms.append(room3)
    course33.possible_rooms.append(room12)
    course34.possible_rooms.append(room2)
    course34.possible_rooms.append(room3)
    course35.possible_rooms.append(room12)
    course35.possible_rooms.append(room11)
    course36.possible_rooms.append(room12)
    course36.possible_rooms.append(room2)

    lesson33_1 = Lesson(whole_semester_group=False)
    lesson33_2 = Lesson(whole_semester_group=False)
    lesson33_3 = Lesson(whole_semester_group=False)
    lesson34_1 = Lesson()
    lesson34_2 = Lesson()
    lesson34_3 = Lesson()
    lesson35_1 = Lesson()
    lesson35_2 = Lesson()
    lesson35_3 = Lesson()
    lesson36_1 = Lesson(timeslot_size=2)
    lesson36_2 = Lesson(timeslot_size=2)

    lesson33_1.teachers.append(teacher7)
    lesson33_2.teachers.append(teacher7)
    lesson33_3.teachers.append(teacher7)
    lesson33_1.teachers.append(teacher11)
    lesson33_2.teachers.append(teacher11)
    lesson33_3.teachers.append(teacher11)
    lesson34_1.teachers.append(teacher26)
    lesson34_2.teachers.append(teacher26)
    lesson34_3.teachers.append(teacher27)
    lesson35_1.teachers.append(teacher9)
    lesson35_2.teachers.append(teacher10)
    lesson35_3.teachers.append(teacher11)
    lesson36_1.teachers.append(teacher25)
    lesson36_2.teachers.append(teacher25)

    course33.lessons.extend([lesson33_1, lesson33_2, lesson33_3])
    course34.lessons.extend([lesson34_1, lesson34_2, lesson34_3])
    course35.lessons.extend([lesson35_1, lesson35_2, lesson35_3])
    course36.lessons.extend([lesson36_1, lesson36_2])

    # ITD
    course37 = Course(abbreviation="DST", name="Darstellungstechniken", type="Vorlesung", is_lecture=True)
    course38 = Course(abbreviation="GProg", name="Grundlagen Programmierung", type="Vorlesung", is_lecture=True)
    course39 = Course(abbreviation="MedT", name="Medientechnik", type="Vorlesung")
    course40 = Course(abbreviation="MedTh", name="Medientheorie", type="Vorlesung")
    course41 = Course(abbreviation="PhyMa1", name="Physik / Mathematik I", type="Vorlesung", only_forenoon=True, is_lecture=True)
    course42 = Course(abbreviation="3DV", name="3D-Animation und Video-Compositing", type="Vorlesung", is_lecture=True)
    course43 = Course(abbreviation="DDM", name="Design Digitaler Medien", type="Vorlesung")
    course44 = Course(abbreviation="DsgnT", name="Designpsychologie", type="Vorlesung", all_in_one_block=True)
    course45 = Course(abbreviation="DV", name="Digitale Verfahren", type="Vorlesung")
    course46 = Course(abbreviation="Konz", name="Konzeption interaktiver Medien", type="Praktika")
    course47 = Course(abbreviation="SWT", name="Softwaretechnik", type="Praktika", is_lecture=True)
    course48 = Course(abbreviation="DBWeb", name="Datenbanken- und Webprogrammierung", type="Übung", is_lecture=True)
    course49 = Course(abbreviation="DsgPr1", name="Designprojekt I", type="Praktika")
    course50 = Course(abbreviation="AudDsg", name="Audiotechnik und Sounddesign", type="Praktika", one_per_day_per_teacher=True)
    course51 = Course(abbreviation="IntDsg", name="Interaktionsdesign", type="Übung")
    course52 = Course(abbreviation="UUP", name="Usability / User Experienced Design", type="Praktika", all_in_one_block=True)

    session.add_all((course37, course38, course39, course40, course41, course42, course43, course44, course45, course46, course47, course48, course49, course50, course51, course52))

    course37.semester_groups.append(semester_group10)
    course38.semester_groups.append(semester_group10)
    course39.semester_groups.append(semester_group10)
    course40.semester_groups.append(semester_group10)
    course41.semester_groups.append(semester_group10)
    course42.semester_groups.append(semester_group11)
    course43.semester_groups.append(semester_group11)
    course44.semester_groups.append(semester_group11)
    course45.semester_groups.append(semester_group11)
    course46.semester_groups.append(semester_group11)
    course47.semester_groups.append(semester_group11)
    course48.semester_groups.append(semester_group12)
    course49.semester_groups.append(semester_group12)
    course50.semester_groups.append(semester_group12)
    course51.semester_groups.append(semester_group12)
    course52.semester_groups.append(semester_group12)

    course37.possible_rooms.append(room3)
    course37.possible_rooms.append(room4)
    course38.possible_rooms.append(room13)
    course38.possible_rooms.append(room3)
    course39.possible_rooms.append(room4)
    course39.possible_rooms.append(room11)
    course40.possible_rooms.append(room4)
    course40.possible_rooms.append(room14)
    course41.possible_rooms.append(room13)
    course42.possible_rooms.append(room14)
    course43.possible_rooms.append(room4)
    course43.possible_rooms.append(room11)
    course44.possible_rooms.append(room12)
    course45.possible_rooms.append(room2)
    course46.possible_rooms.append(room1)
    course46.possible_rooms.append(room2)
    course47.possible_rooms.append(room14)
    course48.possible_rooms.append(room13)
    course49.possible_rooms.append(room12)
    course50.possible_rooms.append(room11)
    course50.possible_rooms.append(room12)
    course51.possible_rooms.append(room9)
    course52.possible_rooms.append(room13)
    course52.possible_rooms.append(room14)

    lesson37_1 = Lesson()
    lesson37_2 = Lesson()
    lesson38_1 = Lesson()
    lesson38_2 = Lesson()
    lesson39_1 = Lesson()
    lesson39_2 = Lesson()
    lesson40_1 = Lesson()
    lesson41_1 = Lesson(whole_semester_group=False)
    lesson41_2 = Lesson(whole_semester_group=False)
    lesson42_1 = Lesson()
    lesson42_2 = Lesson()
    lesson43_1 = Lesson()
    lesson43_2 = Lesson()
    lesson44_1 = Lesson()
    lesson45_1 = Lesson()
    lesson46_1 = Lesson()
    lesson46_2 = Lesson()
    lesson47_1 = Lesson(whole_semester_group=False)
    lesson47_2 = Lesson(whole_semester_group=False)
    lesson48_1 = Lesson()
    lesson49_1 = Lesson()
    lesson50_1 = Lesson(timeslot_size=2)
    lesson50_2 = Lesson(timeslot_size=2)
    lesson51_1 = Lesson()
    lesson52_1 = Lesson()
    lesson52_2 = Lesson()

    lesson37_1.teachers.append(teacher8)
    lesson37_2.teachers.append(teacher8)
    lesson38_1.teachers.append(teacher24)
    lesson38_2.teachers.append(teacher24)
    lesson39_1.teachers.append(teacher11)
    lesson39_2.teachers.append(teacher11)
    lesson40_1.teachers.append(teacher19)
    lesson41_1.teachers.append(teacher13)
    lesson41_2.teachers.append(teacher14)
    lesson42_1.teachers.append(teacher17)
    lesson42_2.teachers.append(teacher17)
    lesson43_1.teachers.append(teacher9)
    lesson43_2.teachers.append(teacher9)
    lesson44_1.teachers.append(teacher7)
    lesson45_1.teachers.append(teacher19)
    lesson46_1.teachers.append(teacher19)
    lesson46_2.teachers.append(teacher19)
    lesson47_1.teachers.append(teacher15)
    lesson47_2.teachers.append(teacher15)
    lesson48_1.teachers.append(teacher14)
    lesson49_1.teachers.append(teacher15)
    lesson50_1.teachers.append(teacher16)
    lesson50_2.teachers.append(teacher16)
    lesson51_1.teachers.append(teacher24)
    lesson52_1.teachers.append(teacher23)
    lesson52_2.teachers.append(teacher23)
    lesson52_1.teachers.append(teacher20)
    lesson52_2.teachers.append(teacher20)

    course37.lessons.extend([lesson37_1, lesson37_2])
    course38.lessons.extend([lesson38_1, lesson38_2])
    course39.lessons.extend([lesson39_1, lesson39_2])
    course40.lessons.extend([lesson40_1])
    course41.lessons.extend([lesson41_1, lesson41_2])
    course42.lessons.extend([lesson42_1, lesson42_2])
    course43.lessons.extend([lesson43_1, lesson43_2])
    course44.lessons.extend([lesson44_1])
    course45.lessons.extend([lesson45_1])
    course46.lessons.extend([lesson46_1, lesson46_2])
    course47.lessons.extend([lesson47_1, lesson47_2])
    course48.lessons.extend([lesson48_1])
    course49.lessons.extend([lesson49_1])
    course50.lessons.extend([lesson50_1, lesson50_2])
    course51.lessons.extend([lesson51_1])
    course52.lessons.extend([lesson52_1, lesson52_2])

    # AIT
    course53 = Course(abbreviation="AnM", name="Angewandte Mathematik", type="Vorlesung", only_forenoon=True, is_lecture=True)
    course54 = Course(abbreviation="DuI", name="Datenbanken und Informationsmanagement", type="Vorlesung", only_forenoon=True, is_lecture=True)
    course55 = Course(abbreviation="DiBi", name="Digitale Bildverarbeitung", type="Vorlesung")
    course56 = Course(abbreviation="IDR", name="Identifikation und digitale Reglersysteme", type="Vorlesung")
    course57 = Course(abbreviation="RuC", name="Rechnungswesen und Controlling", type="Vorlesung", is_lecture=True)
    course58 = Course(abbreviation="Kom", name="Kommunikationstechnik", type="Übung")
    course59 = Course(abbreviation="EnN", name="Energieverteilungsnetzte", type="Übung", all_in_one_block=True, is_lecture=True)
    course60 = Course(abbreviation="IIS", name="Integrated Information Systems", type="Praktika", all_in_one_block=True)

    session.add_all((course53, course54, course55, course56, course57, course58, course59, course60))

    course53.semester_groups.append(semester_group13)
    course54.semester_groups.append(semester_group13)
    course55.semester_groups.append(semester_group13)
    course56.semester_groups.append(semester_group13)
    course57.semester_groups.append(semester_group14)
    course58.semester_groups.append(semester_group14)
    course59.semester_groups.append(semester_group14)
    course60.semester_groups.append(semester_group14)

    course53.possible_rooms.append(room2)
    course53.possible_rooms.append(room3)
    course54.possible_rooms.append(room8)
    course54.possible_rooms.append(room11)
    course55.possible_rooms.append(room4)
    course55.possible_rooms.append(room2)
    course56.possible_rooms.append(room3)
    course57.possible_rooms.append(room7)
    course57.possible_rooms.append(room6)
    course57.possible_rooms.append(room5)
    course58.possible_rooms.append(room4)
    course59.possible_rooms.append(room11)
    course59.possible_rooms.append(room4)
    course60.possible_rooms.append(room3)

    lesson53_1 = Lesson()
    lesson53_2 = Lesson()
    lesson54_1 = Lesson()
    lesson54_2 = Lesson()
    lesson55_1 = Lesson(timeslot_size=2)
    lesson55_2 = Lesson(timeslot_size=2)
    lesson56_1 = Lesson(whole_semester_group=False)
    lesson56_2 = Lesson(whole_semester_group=False)
    lesson57_1 = Lesson()
    lesson57_2 = Lesson()
    lesson58_1 = Lesson()
    lesson58_2 = Lesson()
    lesson59_1 = Lesson(whole_semester_group=False)
    lesson59_2 = Lesson(whole_semester_group=False)
    lesson60_1 = Lesson()
    lesson60_2 = Lesson()

    lesson53_1.teachers.append(teacher15)
    lesson53_2.teachers.append(teacher15)
    lesson54_1.teachers.append(teacher14)
    lesson54_2.teachers.append(teacher15)
    lesson55_1.teachers.append(teacher16)
    lesson55_2.teachers.append(teacher16)
    lesson56_1.teachers.append(teacher22)
    lesson56_2.teachers.append(teacher22)
    lesson57_1.teachers.append(teacher23)
    lesson57_2.teachers.append(teacher23)
    lesson57_1.teachers.append(teacher21)
    lesson57_2.teachers.append(teacher21)
    lesson58_1.teachers.append(teacher5)
    lesson58_2.teachers.append(teacher5)
    lesson59_1.teachers.append(teacher8)
    lesson59_2.teachers.append(teacher8)
    lesson60_1.teachers.append(teacher9)
    lesson60_2.teachers.append(teacher9)

    course53.lessons.extend([lesson53_1, lesson53_2, lesson53_2])
    course54.lessons.extend([lesson54_1, lesson54_2, lesson54_2])
    course55.lessons.extend([lesson55_1, lesson55_2, lesson55_2])
    course56.lessons.extend([lesson56_1, lesson56_2, lesson56_2])
    course57.lessons.extend([lesson57_1, lesson57_2, lesson57_2])
    course58.lessons.extend([lesson58_1, lesson58_2, lesson58_2])
    course59.lessons.extend([lesson59_1, lesson59_2, lesson59_2])
    course60.lessons.extend([lesson60_1, lesson60_2, lesson60_2])

    session.commit()


def generateSmallDataset(session: Session):
    """
    Create a small timetable dataset and insert it into the sqlite database. The data that was
    previously in the database will be deleted.
    The dataset will contain 6 Teachers, 2 SemesterGroups, 5 Rooms, 12 Courses with 23 Lessons.

    Args:
        session: The SQLAlchemy session object.
    """
    dropAll(session)

    # Create some teachers:
    teacher1 = Teacher(abbreviation="t1", study_day_1=MONDAY, study_day_2=MONDAY)
    teacher2 = Teacher(abbreviation="t2", study_day_1=WEDNESDAY, study_day_2=WEDNESDAY, avoid_free_day_gaps=True)
    teacher3 = Teacher(abbreviation="t3", study_day_1=MONDAY, study_day_2=TUESDAY, max_lectures_as_block=3)
    teacher4 = Teacher(abbreviation="t4", study_day_1=TUESDAY, study_day_2=MONDAY, avoid_free_day_gaps=True)
    teacher5 = Teacher(abbreviation="t5", study_day_1=None, study_day_2=None)
    teacher6 = Teacher(abbreviation="t6", study_day_1=None, study_day_2=None)
    teacher1.not_available_timeslots.extend(timeslotsByID(session, 17, 11, 12))
    teacher2.not_available_timeslots.extend(timeslotsByID(session, 11, 12, 9))
    teacher3.not_available_timeslots.extend(timeslotsByID(session, 3, 7))
    teacher5.not_available_timeslots.extend(timeslotsByID(session, 6, 7, 11, 12, 17))

    # Create some semester groups:
    semesterGroup1 = SemesterGroup(study_course="Informatik/Softwaretechnik", abbreviation="INF 1", semester=1, free_day="MO")
    semesterGroup2 = SemesterGroup(study_course="Informatik/Softwaretechnik", abbreviation="INF 6", semester=6)

    # Create some rooms:
    room1 = Room(name="1-1.1")
    room2 = Room(name="2-2.2")
    room3 = Room(name="3-3.3")
    room4 = Room(name="4-4.4")
    room5 = Room(name="5-5.5")
    room1.not_available_timeslots.extend(timeslotsByID(session, 13, 14, 15, 20))
    room2.not_available_timeslots.extend(timeslotsByID(session, 22))

    # Create some courses:
    course1 = createCourse("Bachelorarbeit Seminar", "BAS", "Vorlesung", [3], [teacher3], [semesterGroup2], [room1, room4], isLecture=True)
    course2 = createCourse("Softwareprojekt", "SWP", "Projekt", [2, 1], [teacher2], [semesterGroup2], [room1, room2], allInOneBlock=True, onePerDayPerTeacher=True)
    course3 = createCourse("Informatik I", "INF 1", "Vorlesung", [1, 2], [teacher2], [semesterGroup1], [room3], onlyForenoon=True, isLecture=True, onePerDayPerTeacher=True)
    course4 = createCourse("Mathe I", "MA 1", "Vorlesung", [2, 1], [[teacher3], [teacher1]], [semesterGroup1], [room1, room2], allInOneBlock=True, isLecture=False, onePerDayPerTeacher=False)
    course5 = createCourse("Mathe I Übung", "MA 1 Ü", "Übung", [1, 2], [teacher1, teacher4], [semesterGroup1], [room2], isLecture=True)
    course6 = createCourse("Programmieren I", "Prog 1", "Vorlesung", [1, 2], [teacher3], [semesterGroup1], [room1, room4], onlyForenoon=True, isLecture=True, onePerDayPerTeacher=True)
    course7 = createCourse("Datenbanken", "DB", "Vorlesung", [1], [teacher2], [semesterGroup2], [room1, room3])
    course8 = createCourse("Imaginäres Fach", "IF", "Praktika", [1, 1, 1, 1, 1], [[teacher1], [teacher2], [teacher5], [teacher5], [teacher2], [teacher3]], [semesterGroup1], [room1, room2, room3, room4], wholeSemesterGroup=False)
    course9 = createCourse("Test same time course I", "STC", "Praktika", [2], [teacher6], [semesterGroup1], [room5])
    course10 = createCourse("Test same time course II", "STC2", "Praktika", [1], [teacher6], [semesterGroup1], [room5])
    course11 = createCourse("Datenbanken Praktikum", "DB Pr", "Praktika", [1, 1], [[teacher5], [teacher6]], [semesterGroup2], [room5, room4], wholeSemesterGroup=False)
    course12 = createCourse("Test same time part lessons", "TSP", "Übung", [1, 1], [teacher4], [semesterGroup1, semesterGroup2], [room3], isLecture=True)

    # Add to db:
    session.add_all((teacher1, teacher2, teacher3, teacher4, teacher5, teacher6))
    session.add_all((room1, room2, room3, room4, room5))
    session.add_all((course1, course2, course3, course4, course5, course6, course7, course8, course9, course10, course10, course11, course12))
    session.add_all((semesterGroup1, semesterGroup2))

    # Add lessons_at_same_time and consecutive_lessons relations:
    course9.lessons[0].lessons_at_same_time.append(course10.lessons[0])
    course6.lessons[1].lessons_consecutive.extend(course11.lessons[0:2])
    course12.lessons[0].lessons_at_same_time.append(course12.lessons[1])

    session.commit()


def generateSmallFullTestDataset(session: Session):
    """
    Try to create a timetable in which all constraints occur at least once.
    """

    dropAll(session)

    teacher1 = Teacher(abbreviation="01", name="T1Name", first_name="T1FirstName", study_day_1=MONDAY, study_day_2=FRIDAY)  # Studydays
    teacher2 = Teacher(abbreviation="02", name="T2Name", first_name="T2FirstName", study_day_1=TUESDAY, study_day_2=WEDNESDAY, max_lessons_per_day=4)  # needs more than 4 lesson_timeslots
    teacher3 = Teacher(abbreviation="03", name="T3Name", first_name="T3FirstName", study_day_1=FRIDAY, study_day_2=THURSDAY, max_lectures_per_day=2)  # needs more than 2 lecture_timeslots
    teacher4 = Teacher(abbreviation="04", name="T4Name", first_name="T4FirstName", study_day_1=FRIDAY, study_day_2=FRIDAY, max_lectures_as_block=1)  # needs more than 1 lecture_timeslots
    teacher5 = Teacher(abbreviation="05", name="T5Name", first_name="T5FirstName", study_day_1=MONDAY, study_day_2=TUESDAY, avoid_free_day_gaps=True)
    teacher6 = Teacher(abbreviation="06", name="T6Name", first_name="T6FirstName", study_day_1=WEDNESDAY, study_day_2=WEDNESDAY)
    teacher7 = Teacher(abbreviation="06", name="T7Name", first_name="T7FirstName", study_day_1=None, study_day_2=None)  # Teacher without studyday.
    teacher5.not_available_timeslots.extend(session.query(Timeslot).all()[3:9])
    teacher6.not_available_timeslots.extend(session.query(Timeslot).all()[19:23])

    semesterGroup1 = SemesterGroup(study_course="Studiengang 1", abbreviation="INF1", semester=1, free_day="MO")
    semesterGroup2 = SemesterGroup(study_course="Studiengang 1", abbreviation="INF3", semester=3, max_lessons_per_day=4)  # needs more than 5 lesson_timeslots
    semesterGroup3 = SemesterGroup(study_course="Studiengang 1", abbreviation="INF5", semester=5)
    semesterGroup4 = SemesterGroup(study_course="Studiengang 2", abbreviation="INF7", semester=7)

    room1 = Room(name="1-1.01")
    room2 = Room(name="2-2.02")
    room3 = Room(name="3-3.03")
    room4 = Room(name="4-4.04")
    room5 = Room(name="5-5.05")
    room6 = Room(name="6-6.06")
    room7 = Room(name="7-7.07")
    room1.not_available_timeslots.extend(session.query(Timeslot).all()[1:5])

    course1 = createCourse("Datenbanken", "DB", "Vorlesung", [1, 1], [teacher1], [semesterGroup1], [room1, room2], onlyForenoon=True)

    course2 = createCourse("Informatik I", "INF 1", "Vorlesung", [2, 1], [teacher2], [semesterGroup1], [room1, room2], onlyForenoon=True, isLecture=True)

    course3 = createCourse("Programmieren I Praktikum", "Prog1 Pr", "Praktika", [1, 1, 1, 1], [[teacher4, teacher5], [teacher4, teacher5], [teacher5], [teacher5]], [semesterGroup1], [room3, room4])
    course4 = createCourse("Informatik I Praktikum", "Inf1 Pr", "Praktika", [1, 1, 1, 1], [teacher2], [semesterGroup3], [room3, room4])
    course3.lessons[0].lessons_at_same_time.append(course4.lessons[0])
    course3.lessons[1].lessons_at_same_time.append(course4.lessons[1])
    course3.lessons[2].lessons_at_same_time.append(course4.lessons[2])
    course3.lessons[3].lessons_at_same_time.append(course4.lessons[3])
    course3.lessons[0].available_timeslots.extend(session.query(Timeslot).all()[7:26])
    course3.lessons[0].available_timeslots.extend(session.query(Timeslot).all()[8:24])

    course5 = createCourse("SameTimeTest1", "ST1", "Vorlesung", [2], [teacher5], [semesterGroup2], [room2, room3])
    course6 = createCourse("SameTimeTest2", "ST2", "Vorlesung", [3], [teacher4], [semesterGroup2], [room2, room3])
    course5.lessons[0].lessons_at_same_time.append(course6.lessons[0])

    # Test Consecutive Lessons
    # Test with Lessons of the same Course
    course7 = createCourse("Consecutive Test", "CT", "Vorlesung", [1, 1], [teacher7], [semesterGroup3], [room3, room4], allInOneBlock=True)
    course7.lessons[0].lessons_consecutive.append(course7.lessons[1])

    course8 = createCourse("Lecture1", "L1", "Vorlesung", [1, 1], [teacher3, teacher4], [semesterGroup3], [room5, room6], isLecture=True)

    course9 = createCourse("Praktikum, SameTime", "ST Pr", "Praktikum", [1, 1, 2, 1], [[teacher5], [teacher5], [teacher6], [teacher6]], [semesterGroup2, semesterGroup3], [room6], wholeSemesterGroup=False)
    course9.lessons[0].lessons_at_same_time.append(course9.lessons[1])
    course9.lessons[2].lessons_at_same_time.append(course9.lessons[3])

    course10 = createCourse("GivenTimeCourse", "GTC", "Vorlesung", [1], [teacher7], [semesterGroup3], [room1, room2, room3])
    course10.lessons[0].available_timeslots.append(timeslotByID(session, 12))

    course11 = createCourse("Consecutive Praktikum", "CP", "Praktikum", [1, 1], [teacher2, teacher7], [semesterGroup4], [room7], wholeSemesterGroup=False)
    course12 = createCourse("Consecutive Praktikum2", "CP2", "Praktikum", [1, 1], [teacher7], [semesterGroup3], [room7], wholeSemesterGroup=False)
    course11.lessons[0].lessons_consecutive.append(course12.lessons[0])
    course12.lessons[0].lessons_consecutive.append(course11.lessons[1])
    course11.lessons[1].lessons_consecutive.append(course12.lessons[1])

    course13 = createCourse("AsBlock", "BLCK", "Vorlesung", [2, 1], [[teacher3], [teacher7]], [semesterGroup3], [room7], isLecture=True, wholeSemesterGroup=True, allInOneBlock=True)

    session.add_all([course1, course2, course3, course4, course5, course6, course7, course8, course9, course10, course11, course12, course13])
    session.commit()


def generateBigTrivialDataset(session, n):
    """
    Adds a small timetable n-times to the database.
    For each n, a small timetable will be added:
    3 Teachers,
    1 SemesterGroup,
    3 Rooms,
    5 Courses with 9 Lessons and 15 occupied timeslots.

    The total timetable will have a optimal objective value of 0, in any case.

    Args:
        session: The SQLAlchemy session object.
        n: Number of adding the timetable to the database.
    """
    dropAll(session)

    for i in range(n):
        # Create some teachers:
        teacher1 = Teacher(abbreviation="t1", study_day_1=MONDAY, study_day_2=TUESDAY)
        teacher2 = Teacher(abbreviation="t2", study_day_1=WEDNESDAY, study_day_2=THURSDAY, max_lectures_as_block=3)
        teacher3 = Teacher(abbreviation="t3", max_lectures_as_block=3)
        # Add (up to) 3 not available timeslots for Teacher 1 and 2.
        teacher1.not_available_timeslots.extend(timeslotsByID(session, random.randrange(1, 30, 1), random.randrange(1, 30, 1), random.randrange(1, 30, 1)))
        teacher2.not_available_timeslots.extend(timeslotsByID(session, random.randrange(1, 30, 1), random.randrange(1, 30, 1), random.randrange(1, 30, 1)))

        # Create some semester groups:
        semesterGroup1 = SemesterGroup(study_course="Informatik/Softwaretechnik", abbreviation="INF 6", semester=6)

        # Create some rooms:
        room1 = Room(name="1-1.1")
        room2 = Room(name="2-2.2")
        room3 = Room(name="3-2.2")
        room1.not_available_timeslots.extend(timeslotsByID(session, random.randrange(1, 30, 1), random.randrange(1, 30, 1), random.randrange(1, 30, 1)))
        room2.not_available_timeslots.extend(timeslotsByID(session, random.randrange(1, 30, 1)))

        # Create some courses:
        course1 = createCourse("Bachelorarbeit Seminar", "BAS", "Vorlesung", [3], [teacher3], [semesterGroup1], [room1, room2], isLecture=True)
        course2 = createCourse("Softwareprojekt", "SWP", "Projekt", [2, 1], [teacher2], [semesterGroup1], [room1, room2], onePerDayPerTeacher=True)
        course3 = createCourse("Informatik I", "INF 1", "Vorlesung", [1, 2], [teacher2], [semesterGroup1], [room3], onlyForenoon=True, isLecture=True)
        course4 = createCourse("Mathe I", "MA 1", "Vorlesung", [2, 1], [[teacher3], [teacher1]], [semesterGroup1], [room1, room2], allInOneBlock=True)
        course5 = createCourse("Mathe I Übung", "MA 1 Ü", "Übung", [1, 2], [teacher1, teacher3], [semesterGroup1], [room3])
        # Add lessons_at_same_time and consecutive_lessons relations:
        course1.lessons[0].lessons_at_same_time.append(course3.lessons[0])

        # Add to db:
        session.add_all((teacher1, teacher2, teacher3))
        session.add_all((room1, room2, room3))
        session.add_all((course1, course2, course3, course4, course5))
        session.add(semesterGroup1)

        session.commit()


if __name__ == '__main__':
    engine = create_engine("sqlite:///" + ORM.DB_PATH + "?check_same_thread=False", echo=False)
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()

    dropAll(session)

    # generateBigDataset(session)
    generateSmallDataset(session)
    # generateSmallFullTestDataset(session)
    # generateBigTrivialDataset(session,4)

    teachers = session.query(Teacher)
    print(*teachers, sep="\n")

    rooms = session.query(Room)
    print(*rooms, sep="\n")

    courses = session.query(Course)
    print(*courses, sep="\n")

    semester_groups = session.query(SemesterGroup)
    print(*semester_groups, sep="\n")

    timeslots = session.query(Timeslot)
    print(*timeslots, sep="\n")
