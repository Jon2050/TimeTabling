"""
This file contains the weights for all soft constraints.
Some constraints require more than one weight. This is because
there are different types of violating the constraint.

The values must always be integer numbers greater than or equal to zero.
"""

# ### PreferFirstStudyDayChoiceConstraint ###
# For each first studyday choice that is not realized,
# this value will be added to the Objective Value.
PREFER_FIRST_STUDYDAY_PENALTY = 30

# ### AvoidLateTimeslotsConstraint ###
# For each lesson that takes place in the sixth timeslot of a day,
# this value will bes added to the Objective Value.
SIXTH_HOUR_PENALTY = 5
# For each lesson that takes place in the fifth timeslot of a day,
# this value will bes added to the Objective Value.
FIFTH_HOUR_PENALTY = 3

# ### AvoidEarlyTimeslotsConstraint ###
# For each lesson that takes place in the first timeslot of a day,
# this value will bes added to the Objective Value.
FIRST_HOUR_PENALTY = 2

# ### AvoidGapBetweenLessonsSemesterGroupConstraint ###
# These values will be added to the Objective Value for
# the timeslot-gaps of the respective size, contained in
# the timetable for a semester group.
#
# Gap of one timeslot.
ONE_TIMESLOT_GAP_PENALTY = 3
# Gap of two timeslots.
TWO_TIMESLOT_GAP_PENALTY = 4
# Gap of three timeslots.
THREE_TIMESLOT_GAP_PENALTY = 4
# Gap of four timeslots.
FOUR_TIMESLOT_GAP_PENALTY = 3

# ### AvoidGapBetweenDaysTeacherConstraint ###
# These values will be added to the Objective Value for
# the day-gaps of the respective size, contained in the
# timetable for a teacher. Only applied to teachers this
# constraint is activated for. (variable avoid_free_day_gaps = True)
#
# Gap of one day.
ONE_DAY_GAP_PENALTY = 18
# Gap of two days.
TWO_DAY_GAP_PENALTY = 30
# Gap of three days.
THREE_DAY_GAP_PENALTY = 18

# ### FreeDaySemesterGroupConstraint ###
# This value will be added to the Objective Value for
# each lesson with the respective semester group, that
# takes place on a day that is wished to be free by
# the semester group.
LESSONS_ON_FREE_DAY_PENALTY = 9
