from HelperFunctions import flatMap
from Base import Base
from sqlalchemy import Column, Integer, String


class SemesterGroup(Base):
    """
    Class represent a teacher in the database.
    """

    # The name of the table in the database.
    __tablename__ = 'semester_group'

    # Primary key in the database.
    id = Column(Integer, primary_key=True)
    # Name of the SemesterGroup's study course. Used for timetable output.
    study_course = Column(String, default="")
    # The SemesterGroup's abbreviation. Used for timetable output.
    abbreviation = Column(String, default="")
    # Number of the SemesterGroup's semester. Used for timetable output.
    semester = Column(Integer, default=-1)
    # Max number of Timeslots for the SemesterGroup per day.
    max_lessons_per_day = Column(Integer, default=5)
    # Optionally requested free day. One of the Weekday constants of the Timeslots file.
    free_day = Column(String, default=None)

    # List of all Courses this SemesterGroup participates at.
    # Is set/filled by the Course class which holds the association table object.
    courses = None

    def getLessons(self):
        """
        Get a list of all Lessons in all Courses
        this SemesterGroup participates in.

        Returns: List with all Courses of the SemesterGroup.
        """
        return flatMap(lambda c: c.lessons, self.courses)

    def __repr__(self):
        """
        Gives a textual representation of the SemesterGroup object.

        Returns: A string that represents the SemesterGroup. E.g.:
        "SemesterGroup(id='1', study_course='Informatik/Softwaretechnik', semester='6')"
        """
        return "SemesterGroup(id='%s', study_course='%s', semester='%i')" %\
               (self.id, self.study_course, self.semester)