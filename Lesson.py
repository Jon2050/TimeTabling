from HelperFunctions import flatMap
from Timeslot import Timeslot
from Base import Base
from sqlalchemy import Table, Column, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref, relation

# The table in the database that contains Teacher and Lesson ids to associate
# each Lesson with the teachers who teach the Lesson.
lesson_teacher_association_table = Table('lesson__teacher', Base.metadata,
                                         Column('lesson_id', Integer, ForeignKey('lesson.id')),
                                         Column('teacher_id', Integer, ForeignKey('teacher.id'))
                                         )

# The table in the database that contains Timeslot and Lesson ids to associate
# each Lesson with Timeslot the Lesson can take place at.
lesson_available_timeslots_association_table = Table('available_timeslots__lesson', Base.metadata,
                                                     Column('lesson_id', Integer, ForeignKey('lesson.id')),
                                                     Column('timeslot_id', Integer, ForeignKey('timeslot.id'))
                                                     )

# The table in the database that contains ids of two Lessons to associate
# two Lessons that should take place at the same time.
lessons_at_same_time_association_table = Table('lessons_same_time', Base.metadata,
                                               Column('lesson_1_id', Integer, ForeignKey('lesson.id')),
                                               Column('lesson_2_id', Integer, ForeignKey('lesson.id'))
                                               )

# The table in the database that contains ids of two Lessons to associate
# a Lesson with another Lesson that should take place directly after the first one.
lessons_consecutive_association_table = Table('lessons_consecutive', Base.metadata,
                                              Column('lesson_1_id', Integer, ForeignKey('lesson.id')),
                                              Column('lesson_2_id', Integer, ForeignKey('lesson.id'))
                                              )


class Lesson(Base):
    """
    Class representing a Lesson of a Course in the timetable.
    """

    # The name of the corresponding table in the database.
    __tablename__ = 'lesson'

    # Primary key.
    id = Column(Integer, primary_key=True)
    # Indication whether the Lesson is to be attended by whole SemesterGroups
    # or only by parts of SemesterGroups.
    whole_semester_group = Column(Boolean, default=True)
    # Size of the Lesson as number of Timeslots.
    timeslot_size = Column(Integer, default=1)
    # Id of the corresponding course.
    course_id = Column(Integer, ForeignKey('course.id'))
    # The corresponding Course as object.
    course = relationship("Course", back_populates="lessons")

    # List of all Teachers assigned to this Lesson.
    teachers = relationship("Teacher", secondary=lesson_teacher_association_table,
                            cascade="all,delete", backref=backref("lessons", cascade="all,delete"))
    # List of Timeslots the Lesson can take place at.
    # If empty, no timeslot restriction.
    available_timeslots = relationship("Timeslot", secondary=lesson_available_timeslots_association_table,
                                       cascade="all,delete")
    # List of Lessons that should take place at the same time.
    lessons_at_same_time = relation("Lesson", secondary=lessons_at_same_time_association_table,
                                    primaryjoin=lessons_at_same_time_association_table.c.lesson_1_id == id,
                                    secondaryjoin=lessons_at_same_time_association_table.c.lesson_2_id == id,
                                    cascade="all,delete")
    # List of Lessons that should take place directly after this Lesson.
    lessons_consecutive = relation("Lesson", secondary=lessons_consecutive_association_table,
                                   primaryjoin=lessons_consecutive_association_table.c.lesson_1_id == id,
                                   secondaryjoin=lessons_consecutive_association_table.c.lesson_2_id == id,
                                   cascade="all,delete")

    def getAvailableTimeslots(self, allTimeslots) -> [Timeslot]:
        """
        Returns a list of timeslots the lesson can take place at.
        Considers available Timeslots of the Teachers and only Timeslots
        in the forenoon, if the Lesson can only take place in the forenoon.

        Args:
            allTimeslots: A list with all Timeslots of the timetable.

        Returns: A filtered list of Timeslots the Lesson can take place at.
        """
        # List with all Timeslots any of the Teachers is not available at.
        notAvailableTimeslotsTeachers = flatMap(lambda t: t.not_available_timeslots, self.teachers)
        # notAvailableTimeslotsTeachers = [item for sublist in map(lambda t: t.not_available_timeslots, self.teachers) for item in sublist]
        # If Lesson can only take place on forenoon, create list with all afternoon timeslots.
        if self.course.only_forenoon:
            notAvailableTimeslotsForenoon = list(filter(lambda t: t.number not in Timeslot.getForenoonTimeslotNumbers(), allTimeslots))
        else:
            notAvailableTimeslotsForenoon = []

        timeslots = [x for x in allTimeslots if x not in (notAvailableTimeslotsTeachers + notAvailableTimeslotsForenoon)]
        if self.available_timeslots:  # If list is not empty. Else no restrictions.
            timeslots = [x for x in timeslots if x in self.available_timeslots]

        return timeslots

    def __repr__(self):
        """
        Gives a string representation of the Lesson.
        e.g.: "Lesson(id='1', courseName='Informatik', teachers='[3]', semester_groups='2')"

        Returns: The string representation of the Lesson object.
        """
        return "Lesson(id='%i', courseName='%s', teachers='%s', semester_groups='%s')" % \
               (self.id, self.course.name,
                str(list(map(lambda t: t.id, self.teachers))),
                str(list(map(lambda s: s.id, self.course.semester_groups))))
