import logging
from Timeslot import Timeslot
from Base import Base
from sqlalchemy import Table, Column, Integer, ForeignKey, String, Boolean
from sqlalchemy.orm import relationship, backref
from HelperFunctions import *

# Logger is used in the plausibility check method.
logger = logging.getLogger("TimeTablingLogger")

# The table in the database that contains Course and Room ids to associate
# a Course with the Rooms the Course can take place at.
course_room_association_table = Table('course__room', Base.metadata,
                                      Column('course_id', Integer, ForeignKey('course.id')),
                                      Column('room_id', Integer, ForeignKey('room.id'))
                                      )

# The table in the database that contains Course and SemesterGroup ids to associate
# the Courses with the SemesterGroups that participate at the Courses.
course_semester_group_association_table = Table('course__semester_group', Base.metadata,
                                                Column('course_id', Integer, ForeignKey('course.id')),
                                                Column('semester_group_id', Integer, ForeignKey('semester_group.id'))
                                                )


class Course(Base):
    """
    Class representing a Course of the timetable.
    """

    # Name of the corresponding table in the database.
    __tablename__ = 'course'

    # Primary key of the Course.
    id = Column(Integer, primary_key=True)
    # Courses name. Used for timetable output.
    name = Column(String)
    # Courses abbreviation. Used for timetable output.
    abbreviation = Column(String)
    # Courses type. Used for timetable output.
    type = Column(String)
    # Indicates whether the Lessons of the Course may only take place in the forenoon.
    only_forenoon = Column(Boolean, default=False)
    # Indicates whether all Lessons of the Course should take place as a block.
    all_in_one_block = Column(Boolean, default=False)
    # Indicates whether the Course should be counted as a lecture.
    is_lecture = Column(Boolean, default=False)
    # Indicates whether the Course is a onePerDayPerTeacher course.
    # For every Teacher, only Lessons of one of such Courses can take place on one day.
    one_per_day_per_teacher = Column(Boolean, default=False)

    # List with rooms the Lessons of the Course can take place at.
    possible_rooms = relationship("Room", secondary=course_room_association_table, cascade="all,delete",
                                  backref=backref("possible_courses", cascade="all,delete"))
    # List of the SemesterGroups participating in this Course.
    semester_groups = relationship("SemesterGroup", secondary=course_semester_group_association_table,
                                   cascade="all,delete", backref=backref("courses", cascade="all,delete"))
    # List with all Lessons of the Course.
    lessons = relationship("Lesson", back_populates="course")

    def getTeachers(self):
        """
        Get a list of all Teachers assigned to any of the Courses Lessons.

        Returns: A list with all assigned Teachers.
        """
        return list(set(flatMap(lambda l: l.teachers, self.lessons)))

    # Call only after the timeVars of the Lessons have been created!
    # (HardConstraints: createTimeAndRoomVariables)
    def getAllTimeVars(self):
        """
        Get a list of all timeVars of any Lesson of this Course.
        These variables are created in the function createTimeAndRoomVariables
        on the file HardConstraints.py. Call this method only after the function
        already has been called.

        Returns: A list with timeVar (IntVar) variables of all Lessons of this Course.
        """
        return flat(map(lambda l: l.timeVars, self.lessons))

    def plausibilityCheck(self,orm, preString) -> bool:
        """
        Performs a superficial plausibility check of the
        Course's attributes. It is checked whether all Lessons
        fit in available time windows of the Course. E.g. if all Lessons
        fit in the forenoon Timeslots if this is a onlyForenoon Course.

        Will cause logger messages on failed checks.

        Args:
            preString: A string added at first of each logger message.

        Returns: True if all checks passed. False if at least on check failed.
        """
        plausible = True
        # The time window is either the morning period or
        # max Lesson per day of the Teachers and SemesterGroups.
        maxLessonPerDay = min([x.max_lessons_per_day for x in self.getTeachers()]+[x.max_lessons_per_day for x in self.semester_groups])
        maxTimeWindow = len(Timeslot.getForenoonTimeslotNumbers()) if self.only_forenoon else orm.TIMESLOTS_PER_DAY
        maxTimeWindow = min([maxLessonPerDay, maxTimeWindow])

        # Check single Lessons.
        if max([x.timeslot_size for x in self.lessons]) > maxTimeWindow:
            logger.error(preString + "[Infeasible data] Course: id=%i %2s, has a to long Lesson: size > %i" %
                         (self.id, self.name, max(map(lambda l: l.timeslot_size, self.lessons)), maxTimeWindow))
            plausible = False

        # Check if all Lessons fit in one day if the Course is allInOneBlock.
        # Could led to false positives. E.g. for courses with PartSemesterGroup lessons.
        if self.all_in_one_block:
            totalLength = sum(map(lambda l: l.timeslot_size, self.lessons))
            if totalLength > maxTimeWindow:
                logger.error(preString + "[Data Infeasible]Course: id=%i %2s, all_in_one_block lessons have a length of %i but max_lessons_per_day = %i" %
                             (self.id, self.name, totalLength, maxTimeWindow))
                plausible = False

        return plausible

    def __repr__(self):
        """
        Gives a textual representation of the Course object.

        Returns: A string that represents the Course. E.g.:
        Course(id='2', name='Informatik', lessonCount='2', teacherIDs='[3]', semesterGroup='[4,5]')"
        """
        return "Course(id='%s', name='%s', lessonCount='%i', teacherIDs='%s', semesterGroups='%s')" % \
               (self.id, self.name, len(self.lessons),
                str([x.id for x in self.getTeachers()]), str([x.id for x in self.semester_groups]))
