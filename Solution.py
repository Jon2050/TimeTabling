import Room
from HardConstraints import *
from Lesson import Lesson

LESSON_IDX = 0
ROOM_IDX = 1


class Solution:
    """
    A representation of a found timetable solution.
    Contains a map with lists of tuples for each timeslot.
    Each tuple contains a lesson and the corresponding room,
    that takes place at the timeslot.
    """

    def __init__(self, solutionIndex, orm: ORM, objectiveValue=0):
        # Creates a empty solution object.
        self.solutionIndex = solutionIndex
        self.orm = orm
        self.objectiveValue = objectiveValue
        self.timeslotMap = {}
        for timeslot in orm.getTimeslots():
            self.timeslotMap[timeslot] = []  # map a list with lessons to eacht timeslot

    def addLesson(self, lesson: Lesson, room: Room, timeslot):
        """
        Adds a lesson with room to the timetable.

        Args:
            lesson: The lesson to add to the timetable.
            room: The room, the lesson takes place at.
            timeslot: The timeslot, the lesson takes place at.
        """
        self.timeslotMap[timeslot].append((lesson, room))

    def getTimeTableMap(self):
        """
        Returns: The map [timeslot -> (lesson, room)], that contains the whole timetable solution.
        """
        return self.timeslotMap

    def getLessonsAtTimeslot(self, timeslot):
        """
        Args:
            timeslot: A timeslot of the timetable.

        Returns: A list with tuples of all lessons, that take place at the given timeslot.
        Each tuple in the list contains a lesson as first element and the room, the lesson takes
        place in, as second element.
        """
        return list(map(lambda tu: tu[LESSON_IDX], self.timeslotMap[timeslot]))

    def getRoomOfLesson(self, lesson):
        """
        Args:
            lesson: A lesson of the timetable. Has to be added to this solution object.

        Returns: The room, the lesson takes place in.
        """
        for tupleList in self.timeslotMap.values():  # each tuple contains a lesson and the corresponding room
            for tu in tupleList:
                if tu[LESSON_IDX] == lesson:
                    return tu[ROOM_IDX]

    def getTimeslotsOfLesson(self, lesson):
        """
        Args:
            lesson: A lesson of the timetable. Has to be added to this solution object.

        Returns: The timeslot, the given lesson takes place at.
        """
        timeslots = []
        for item in self.timeslotMap.items():
            for tu in item[1]:  # value of the dictionary item contains the tuple list
                if tu[LESSON_IDX] == lesson:
                    timeslots.append(item[0])  # key of the dictionary item is the timeslot the lesson take place at
        return timeslots
