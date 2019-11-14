from Base import Base
from sqlalchemy import Column, Integer, String

# Constant for the strings used to name weekdays in the database.
# Use this constants to compare with weekday information like the
# wished studyday for Teachers or the wished free day for SemesterGroups.
MONDAY = "MO"
TUESDAY = "TU"
WEDNESDAY = "WE"
THURSDAY = "TH"
FRIDAY = "FR"


class Timeslot(Base):
    """
    Class representing a timeslot in the timetable.
    Each Timeslot will have the same length.
    """

    # The name of the timeslot table in the database.
    __tablename__ = 'timeslot'

    # Primary Key name. Used to represent each
    # Timeslot object in the timetable search process as an int.
    id = Column(Integer, primary_key=True)
    # String for the weekday the Timeslot takes place at.
    # Should be one of the above defined string constants.
    weekday = Column(String)
    # The number of the weekday the Timeslot takes place at.
    # First weekday e.g. monday should start with 1 the second
    # should have the number 2 and so on.
    weekday_number = Column(Integer)
    # The number of the Timeslot at the day the Timeslot takes place at.
    # 1 for the first Timeslot of a day.
    number = Column(Integer)
    # A string to name the start time the Timeslot starts at.
    # The column name in the database is "from".
    # Only used for timetable output.
    from_time = Column("from", String)
    # A string to name the end time the Timeslot ends at.
    # The column name in the database is "to".
    # Only used for timetable output.
    to_time = Column("to", String)

    def __repr__(self):
        """
        Gives a string representation of the Timeslot.
        e.g.: "Timeslot(id=' 1', MO 1.: 08:15 to 09:45)"

        Returns: The string representation of the Timeslot object.
        """
        return "Timeslot(id='%2s', %s %i.: %s to %s)" % \
               (self.id, self.weekday, self.number, self.from_time, self.to_time)

    @staticmethod
    def getWeekdayID(weekday: String) -> int:
        """
        Maps a weekday string from the weekday string constants to the weekday number.
        Args:
            weekday: The string of the weekday. One of the weekday string constants.

        Returns: The number of the weekday. Starts with 1 for the first weekday.
        """
        days = {MONDAY: 1, TUESDAY: 2, WEDNESDAY: 3, THURSDAY: 4, FRIDAY: 5}
        return days[weekday]

    @staticmethod
    def getForenoonTimeslotNumbers():
        """
        Get a list of the numbers of the Timeslots that take place at forenoon.
        Does not return a list of all IDs of the Timeslots that take place at forenoon,
        only the numbers that represent the number of a Timeslot on a day.
        E.g. [1, 2, 3] if the first 3 Timeslots per day take place at forenoon.
        If alter the Timeslot data e.g. for another timetable model with 45 min slots and
        12 Timeslots per day, this list has to be changed also.

        Returns: The list of the numbers of Timeslots that take place at forenoon.
        """
        return [1, 2, 3]
