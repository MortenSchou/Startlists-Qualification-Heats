# -*- coding: utf-8 -*-
"""
@author: Rudy Rooman rudy.rooman@gmail.com
"""

# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals
from ortools.linear_solver import pywraplp
import timeit
import xlsxwriter
import pandas as pd
import datetime
from random import sample
import sys
import random


class Runner:
    def __init__(self):
        self.ID = 0
        self.FED = ''
        self.Surname = ''
        self.Firstname = ''
        self.StartGrp = 0
        self.RankingPoints = 0
        self.Rank = 0
        self.Heat = 0
        self.Time = 0
        runners.append(self)

    def find_rank(self, _runners):
        self.Rank = 1 + _runners.index(self)

    def __str__(self):
        return str(self.Firstname + " " + self.Surname)


class Nation:
    def __init__(self):
        self.FED = ''
        self.count = 0
        nations.append(self)

    def countrunners(self, _runners):
        self.count = len([_r for _r in _runners if self.FED == _r.FED])


def find_heats_time(_runners, _heats, _nations, _z):
    solver = pywraplp.Solver('SolveAssignmentProblemMIP', pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING)
    random.shuffle(_runners)
    # define runners per heat
    base = len(_runners) // _heats
    runners_per_heat = [base for _h in range(1, _heats + 1)]
    for c in range(len(_runners) - base * _heats):
        runners_per_heat[c] += 1
    print('runners per heat: %s' % runners_per_heat)
    print()

    # startingblocks given by teammanagers ( 0 = no preference, 1 = early, 2 mid section, 3 =late)
    # count runners per starting block
    starting_blocks = [len([_r for _r in runners if _r.StartGrp == sb]) for sb in range(4)]
    # add runners without startblock preference to startgroup with least athletes
    index = starting_blocks.index(min(starting_blocks[1:]))
    starting_blocks[index] += starting_blocks[0]
    starting_blocks = starting_blocks[1:]
    print('runners per starting block: %s' % starting_blocks)
    print()

    # define random runners to be fixed to heats
    random_runners = sample(range(1, len(_runners)), _heats)
    print('Following runners are fixed to a heat to ensure random startlists.')
    for rank in random_runners:
        for _r in runners:
            if _r.Rank == rank:
                print('%s to heat %i.' % (_r, 1+random_runners.index(rank)))

    # [ START create variables ]
    match = {}
    for _r in _runners:
        for _h in range(1, _heats+1):
            for _t in range(runners_per_heat[_h-1]):
                match[_r, _h, _t] = solver.BoolVar('match[%s,%s,%s]' % (_r, _h, _t))

    # [ END create variables ]

    # [ START Constraints ]

    # Each runner is assigned to exactly 1 heat / time combination
    for _r in _runners:
        solver.Add(solver.Sum([match[_r, _h, _t] for _h in range(1, _heats + 1)
                               for _t in range(runners_per_heat[_h-1])]) == 1)

    # each heat / time combination is assigned to exactly 1 runner
    for _h in range(1, _heats + 1):
        for _t in range(runners_per_heat[_h-1]):
            solver.Add(solver.Sum([match[_r, _h, _t] for _r in _runners]) == 1)

    # balance number of runners from 1 country to a heat
    for _n in _nations:
        for _h in range(1, _heats + 1):
            solver.Add(solver.Sum([match[_r, _h, _t] for _t in range(runners_per_heat[_h-1]) for _r in _runners if _r.FED == _n.FED])
                       <= (1 + (_n.count-1) // _heats))
            solver.Add(solver.Sum([match[_r, _h, _t] for _t in range(runners_per_heat[_h-1]) for _r in _runners if _r.FED == _n.FED])
                       >= (_n.count // _heats))

    # spreading runners 1,2,3 over different heats
    for _r1 in runners:
        if (_r1.Rank % _heats) == 1:
            for _r2 in runners:
                if _r2.Rank == _r1.Rank + 1:
                    for _r3 in runners:
                        if _r3.Rank == _r1.Rank + 2:
                            for _h in range(1, _heats + 1):
                                solver.Add(solver.Sum([match[_r1, _h, _t]+match[_r2, _h, _t] + match[_r3, _h, _t]
                                                       for _t in range(runners_per_heat[_h-1])]) <= 1)

    # consecutive times not from same nation
    for _r1 in _runners:
        for _r2 in _runners:
            if _r1.FED == _r2.FED and _r1 != _r2:
                for _h in range(1, _heats + 1):
                    for _t in range(runners_per_heat[_h - 1] - 1):
                        solver.Add(match[_r1, _h, _t] + match[_r2, _h, _t+1] <= 1)

    # comply with startgroup requests
    # a parameter _z for relaxation is available but not used
    for _r in _runners:
        if _r.StartGrp > 1:
            solver.Add(solver.Sum([match[_r, _h, _t] * _t for _h in range(1, _heats + 1)
                                   for _t in range(runners_per_heat[_h-1])]) >=
                       ((sum(starting_blocks[0:_r.StartGrp-1]) - 1) // _heats - _z))
        if _r.StartGrp < _heats and _r.StartGrp != 0:
            solver.Add(solver.Sum([match[_r, _h, _t] * _t for _h in range(1, _heats + 1)
                                   for _t in range(runners_per_heat[_h - 1])]) <=
                       ((sum(starting_blocks[0:_r.StartGrp]) - 1) // _heats + _z))

    # fix random runners to specific heats and time
    for _h in range(1, _heats + 1):
        for _r in _runners:
            if _r.Rank == random_runners[_h-1]:
                solver.Add(solver.Sum([match[_r, _h, _t] for _t in range(runners_per_heat[_h - 1])]) == 1)
    
    # [ END Constraints ]

    # [ START Objectives ]

    # [ END Objectives ]

    sol = solver.Solve()

    if sol == solver.OPTIMAL:
        print()
        if _z == 0:
            print('Starting times: Optimal solution found')
        elif _z > 0:
            print('Starting times: Solution found with correction factor = %i' % _z)
        for _h in range(1, _heats + 1):
                for _r in _runners:
                    for _t in range(runners_per_heat[_h - 1]):
                        if match[_r, _h, _t].solution_value() == 1:
                            _r.Heat = _h
                            _r.Time = _t
    if sol == solver.OPTIMAL:
        txt = 'OPTIMAL'
    else:
        txt = 'FAILED'

    return solver, txt


# ###program starts here### #
heats = 3

# list of instances
runners = []
nations = []

start_time = timeit.default_timer()

# Get file paths and input sheet_name from console parameters.
entries_file = str(sys.argv[1]) if len(sys.argv) > 1 else 'entries.xlsx'
start_list_file = str(sys.argv[2]) if len(sys.argv) > 2 else 'startlists.xlsx'
sheet_name = str(sys.argv[3]) if len(sys.argv) > 3 else 0
first_bib = int(sys.argv[4]) if len(sys.argv) > 4 else 1
time_offset = int(sys.argv[5]) if len(sys.argv) > 5 else 0
skip_rows = 0 if len(sys.argv) > 1 else 3  # The default 'entries.xlsx' has three blank rows before the header.

# read entered runners data file
df = pd.ExcelFile(entries_file)

sheet1 = df.parse(sheet_name)
for teller in range(skip_rows, len(sheet1)):
    # read a row
    row1 = sheet1.iloc[teller]
    # row1 = row1.real
    try:
        runner = Runner()
        runner.ID = row1[0]
        runner.FED = row1[1]
        runner.Surname = row1[2]
        runner.Firstname = row1[3]
        runner.StartGrp = row1[4]
        runner.RankingPoints = row1[5]
    except:
        None

# create country instances
for r in runners:
    countries = [nation.FED for nation in nations]
    if r.FED not in countries:
        nation = Nation()
        nation.FED = r.FED

# count runners per nation
for n in nations:
    n.countrunners(runners)

# sort participants based on ranking
runners = sorted(runners, key=lambda x: x.RankingPoints, reverse=True)

print('We have %i entries.' % len(runners))

for r in runners:
    r.find_rank(runners)

z = 0
while True:
    solution, optimal_result = find_heats_time(runners, heats, nations, z)
    if optimal_result == 'OPTIMAL':
        break
    z += 1

# sort participants based on heat, starttimes
runners = sorted(runners, key=lambda x: (x.Heat, x.Time))

# print en export to Excel
workbook = xlsxwriter.Workbook(start_list_file)
# engineer data from Clicksoftware
startlist_sheet = workbook.add_worksheet('startlist')
row = 0
col = 0
startlist_sheet.write(row, col  , 'IOF ID')
startlist_sheet.write(row, col+1, 'Organisation')
startlist_sheet.write(row, col+2, 'Surname')
startlist_sheet.write(row, col+3, 'First name')
startlist_sheet.write(row, col+4, 'Heat')
startlist_sheet.write(row, col+5, 'Start Time')
startlist_sheet.write(row, col+6, 'Bib')
startlist_sheet.write(row, col+7, 'Start Group')
# startlist_sheet.write(row, col+7, 'Rank')
# startlist_sheet.write(row, col+8, 'Score (based on ranking points)')
heat_names=["A","B","C"]
row = 1
for r in runners:
    print(r.Heat, r.Time, r, r.FED, r.Rank, r.ID, sep =";")
    startlist_sheet.write(row, col  , r.ID)
    startlist_sheet.write(row, col+1, r.FED)
    startlist_sheet.write(row, col+2, r.Surname)
    startlist_sheet.write(row, col+3, r.Firstname)
    startlist_sheet.write(row, col+4, heat_names[r.Heat-1])
    startlist_sheet.write(row, col+5, r.Time + time_offset)
    startlist_sheet.write(row, col+6, r.Heat-1 + r.Time*3 + first_bib)
    startlist_sheet.write(row, col+7, r.StartGrp)
    # startlist_sheet.write(row, col+7, r.Rank)
    # startlist_sheet.write(row, col+8, r.RankingPoints)
    row += 1

workbook.close()

elapsed = timeit.default_timer() - start_time

print()
print('Calculation time: %s seconds.' % round(elapsed, 3))



#
# Verification
#

dfver = pd.DataFrame([vars(r) for r in runners])
#print("Number of runners per federation")
#print(dfver.groupby('FED').count()[['ID']])

print("******************")
print("Number of runners per federation & heat")
print(dfver.groupby(['FED','Heat']).count()[['ID']])


print("******************")
print("Number of runners per federation & heat - min, max and diff")

runnersperheat = dfver.groupby(['FED','Heat']).count()[['ID']]

t = runnersperheat.assign(ID=runnersperheat.ID.abs())\
    .groupby('FED')\
    .ID.agg([('Min','min'),('Max','max')])\
    .add_prefix('Count')

t['Diff'] = t.apply ( lambda row: row.CountMax-row.CountMin, axis=1)
print(t)

max_per_heat = dfver.groupby('Heat').count()[['ID']].max()[0]

for n in range(5, max_per_heat, 5):
    print("******************")
    print(f"Average ranking points of top {n} in each heat")
    rpn = dfver.sort_values('RankingPoints', ascending=False).groupby('Heat').head(n).groupby('Heat').mean()[['RankingPoints']]
    print (rpn)

print("******************")
print("Average ranking points (all)")
rp = dfver.groupby('Heat').mean()[['RankingPoints']]
print (rp)

