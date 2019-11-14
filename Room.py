from Base import Base
from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship

# The table in the database that contains room and timeslot ids to associate
# the timeslots for each room the room is not available at.
not_available_association_table = Table('not_available_timeslots__room', Base.metadata,
                                        Column('room_id', Integer, ForeignKey('room.id')),
                                        Column('timeslot_id', Integer, ForeignKey('timeslot.id'))
                                        )


class Room(Base):
    """
    Class representing a room in the timetable.
    """

    # The name of the table in the database.
    __tablename__ = 'room'

    # The primary key. Is used to represent the room in the CpModel.
    id = Column(Integer, primary_key=True)
    # A textual representation of the room.
    # Used for the timetable output.
    name = Column(String)

    # List with not available Timeslots for the room.
    not_available_timeslots = relationship("Timeslot",
                                           secondary=not_available_association_table,
                                           cascade="all,delete")

    def __repr__(self):
        """
        Gives a string representation of the Room.
        e.g.: "Room(id='3', name='1-02.15')"

        Returns: The string representation of the Room object.
        """
        return "Room(id='%s', name='%s')" % (self.id, self.name)
