from Base import Base
from sqlalchemy import Column, Integer, String, Table, ForeignKey, Boolean
from sqlalchemy.orm import relationship
import logging

# Logger is used in the plausibility check method.
logger = logging.getLogger("TimeTablingLogger")

# The table in the database that contains teacher and timeslot ids to associate
# the timeslots for each teacher he is not available at.
not_available_association_table = Table('not_available_timeslots__teacher', Base.metadata,
                                        Column('teacher_id', Integer, ForeignKey('teacher.id')),
                                        Column('timeslot_id', Integer, ForeignKey('timeslot.id'))
                                        )


class Teacher(Base):
    """
    Class represent a teacher in the database.
    """

    # The name of the table in the database.
    __tablename__ = 'teacher'

    # Primary key in the database table.
    id = Column(Integer, primary_key=True)
    # Last name of the teacher. Used for timetable output.
    name = Column(String, default="")
    # First name, used for timetable output.
    first_name = Column(String, default="")
    #  A short and unique abbreviation. Used for timetable output.
    abbreviation = Column(String, default="")
    # First and second choice for the teacher's studyday.
    # One of the Timeslot weekday constants or null if the teacher has no studyday.
    study_day_1 = Column(String)
    study_day_2 = Column(String)
    # Maximum number of Timeslots to take place at a single day for the Teacher.
    max_lessons_per_day = Column(Integer, default=5)
    # Maximum number of lecture Timeslots to take place at a single day for the Teacher.
    max_lectures_per_day = Column(Integer, default=3)
    # Maximum number of lecture Timeslots in a row for the Teacher.
    max_lectures_as_block = Column(Integer, default=2)
    # Activates the AvoidGapBetweenDaysTeacherConstraint.
    avoid_free_day_gaps = Column(Boolean, default=False)

    # List with Timeslots the Teacher is not available at.
    not_available_timeslots = relationship("Timeslot", secondary=not_available_association_table, cascade="all,delete")

    # List of all Lessons this Teacher teaches.
    # Is set/filled by the Lesson class which holds the association table object.
    lessons = None

    def hasStudyday(self):
        """
        Returns True if the Teacher has a studyday,
        which means none of the two studyday fields are null/None.

        Returns: True if both studyday fields are not None.
        """
        return self.study_day_1 is not None and self.study_day_2 is not None

    def getStudyDayTimeslots1(self, timeslots):
        """
        Get a list with all Timeslots of the Teacher's first studyday choice.

        Args:
            timeslots: An iterable with all Timeslots of the timetable.

        Returns: All timeslots on the Teacher's first study day choice.
                Will return an empty list if the Teacher has no studyday or
                the given timeslots does not contain Timeslots of the studyday choice.
        """
        return list(filter(lambda t: t.weekday == self.study_day_1, timeslots))

    def getStudyDayTimeslots2(self, timeslots):
        """
        Get a list with all Timeslots of the Teacher's second studyday choice.

        Args:
            timeslots: An iterable with all Timeslots of the timetable.

        Returns: All timeslots on the Teacher's second study day choice.
                Will return an empty list if the Teacher has no studyday or
                the given timeslots does not contain Timeslots of the studyday choice.
        """
        return list(filter(lambda t: t.weekday == self.study_day_2, timeslots))

    def getCourses(self):
        """
        Gives a list of all courses of which the teacher
        participates in at least one lesson.

        Returns: The list of all courses the Teacher participates at.
        """
        return list(set(map(lambda l: l.course, self.lessons)))

    def plausibilityCheck(self, orm, preString) -> bool:
        """
        Performs a superficial plausibility check of the
        teacher's attributes. It is checked whether the
        maxLessons and the maxLectures attributes ever
        allow a timetable for the teacher.

        Will cause logger messages on failed checks.

        Args:
            orm: A reference to the ORM script.
            preString: A string added at first of each logger message.

        Returns: True if all checks passed. False if at least on check failed.
        """
        # Number of Timeslots for the Teacher.
        lessonHours = sum(l.timeslot_size for l in self.lessons)
        # Gives a rough upper estimate of how many timeslots the teacher is available in a week.
        hoursAvailable = len(orm.getTimeslots()) \
                         - len(self.not_available_timeslots) \
                         - (orm.TIMESLOTS_PER_DAY if self.hasStudyday() else 0)  # Not available timeslots on the studyday may be counted twice.
        # Number of lecture Timeslots for the Teacher.
        lectureHours = sum(l.course.is_lecture * l.timeslot_size for l in self.lessons)
        # The maximum Lesson size of the Teacher's Lessons.
        maxTimeslotSize = max(l.timeslot_size for l in self.lessons)
        # The maximum lecture Lesson size of the Teacher's lecture Lessons.
        maxLectureTimeslotSize = max(l.course.is_lecture * l.timeslot_size for l in self.lessons)
        # Number of 'OnePerDay' Courses.
        onePerDayCourses = len(list(filter(lambda c: c.one_per_day_per_teacher, self.getCourses())))

        plausible = True
        if lessonHours > hoursAvailable:
            logger.error(preString + "[Infeasible data] Teacher: id=%i %2s, more lesson Timeslots than available Timeslots: %i > %i" % (self.id, self.abbreviation, lessonHours, hoursAvailable))
            plausible = False
        if maxLectureTimeslotSize > self.max_lectures_as_block:
            logger.error(preString + "[Infeasible data] Teacher: id=%i %2s, %i hour lecture but max lectures as block = %i" % (self.id, self.abbreviation, maxLectureTimeslotSize, self.max_lectures_as_block))
            plausible = False
        if lessonHours > (orm.WEEKDAYS - 1 if self.hasStudyday() else orm.WEEKDAYS) * self.max_lessons_per_day:
            logger.error(preString + "[Infeasible data] Teacher: id=%i %2s, to much lessonHours: %i > %i" % (self.id, self.abbreviation, lessonHours, (5 if self.hasStudyday() else 6) * self.max_lessons_per_day))
            plausible = False
        if lectureHours > (orm.WEEKDAYS - 1 if self.hasStudyday() else orm.WEEKDAYS) * self.max_lectures_per_day:
            logger.error(preString + "[Infeasible data] Teacher: id=%i %2s, to much lectureHours: %i > %i" % (self.id, self.abbreviation, lectureHours, (5 if self.hasStudyday() else 6) * self.max_lectures_per_day))
            plausible = False
        if maxTimeslotSize > self.max_lessons_per_day:
            logger.error(preString + "[Infeasible data] Teacher: id=%i %2s, %i hour lesson but max lessons per day = %i" % (self.id, self.abbreviation, maxTimeslotSize, self.max_lessons_per_day))
            plausible = False
        if onePerDayCourses > (orm.WEEKDAYS - 1 if self.hasStudyday() else orm.WEEKDAYS):
            logger.error(preString + "[Infeasible data] Teacher: id=%i %2s, %i courses with only one course per day per teacher" % (self.id, self.abbreviation, onePerDayCourses))
            plausible = False

        return plausible

    def __repr__(self):
        """
        Gives a textual representation of the Teacher object.

        Returns: A string that represents the Teacher. E.g.:
        "Teacher(id='1', abbr='abc', studyday1='MO', studyday2='FR')"
        """
        return "Teacher(id='%s', abbr='%s', studyday1='%s', studyday2='%s')" % \
               (self.id, self.abbreviation, self.study_day_1, self.study_day_2)
