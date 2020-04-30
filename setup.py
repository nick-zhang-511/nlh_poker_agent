#!/usr/bin/env

import abstractions
import mechanics
import pbots_calc

import csv
import json
import os.path
import numpy as np
import pandas as pd
import sys

from itertools import combinations
from scipy.spatial import distance
from sklearn.cluster import KMeans

from pokereval.card import Card

# Specify predefined opening ranges

def BUILD_RANGE_DICTIONARY():
	"""
	Private function that maps each one of 169 preflop hands to one of 8 ranges.
	Writes this map to a JSON file named ''
	** ONLY HAVE TO RUN THIS ONCE **
	"""
	if os.path.isfile('./jsons/HAND_TO_RANGE_MAP.json') and os.path.isfile('./jsons/RANGE_TO_HANDS_MAP.json'):
		print("Range maps already generated. Proceeding.")
		return

	rangeToHands = {

		0 : ['82o', '83o', \
					'72', '73', '74o', \
					'62', '63', '64', '65o', \
					'52', '53', '54', \
					'42', '43', \
					'32'],
		1 : ['J2o', 'J3o', \
				'T2', 'T3o', 'T4o', 'T5o', \
				'92', '93', '94', '95o', \
				'82s', '83s', '84', '85o', \
				'74s', '75o'],
		2 : ['T3s', 'T4s', 'T5s', 'T6', 'T7o', 'T8o', \
				'95s', '96', '97', '98', \
				'85s', '86', '87', \
				'75s', '76', \
				'65s'],
		3 : ['22', \
				'K2', 'K3o', 'K4o', \
				'Q2', 'Q3', 'Q4', 'Q5', 'Q6o', 'Q7o', \
				'J2s', 'J3s', 'J4', 'J5', 'J6', 'J7o'],
		4 : ['Q6s', 'Q7s', 'Q8', 'Q9', 'QTo', 'QJo', \
				'J7s', 'J8', 'J9', 'JT', \
				'T7s', 'T8s', 'T9'], 
		5 : ['33', '44', '55', \
				'K3s', 'K4s', 'K5', 'K6', 'K7', 'K8', 'K9o', \
				'A2', 'A3', 'A4', 'A5', 'A6', 'A7o', 'A8o'],
		6 : ['66', '77', \
				'A7s', 'A8s', 'A9', 'AT', 'AJ', 'AQ', 'AK', \
				'K9s', 'KT', 'KJ', 'KQ', \
				'QTs', 'QJs'],
		7 : ['88', '99', 'TT', 'JJ', 'QQ', 'KK', 'AA'],
	}

	handToRange = {}

	# Populate handToLevel dictionary
	for range_ in rangeToHands:
		hands = rangeToHands[range_]
		for hand in hands:
			if hand[0] == hand[1] or 'o' in hand or 's' in hand:
				handToRange[hand] = range_
			else:
				for x in ['o', 's']:
					handToRange[hand + x] = range_
	
	with open('./jsons/HAND_TO_RANGE_MAP.json', 'w') as filepath:
		json.dump(handToRange, filepath)
	with open('./jsons/RANGE_TO_HANDS_MAP.json', 'w') as filepath:
		json.dump(rangeToHands, filepath)

# Build hand abstraction tools

def _generate_boards(board_size):
	"""
	Generates all boards of specified length
	@board_size

	Returns list of integers representing cards on the board
	"""
	return list(combinations(range(52), board_size))

def _generate_all_hands():
	hands = _generate_boards(2)
	return hands

def _generate_all_boards():
	boards = _generate_boards(3) + _generate_boards(4) # only training on flops and turns
	return boards

def generate_hand_board_combos(board_field, hand_field):
	'''
	CITATION: This abstraction strategy for NLH is adopted. Please see strategy report for full citation.

	@board_field: a list of all possible boards, represented as lists of integers
	@hand_field: a list of all possible hands, represented as lists of integers
	'''

	if os.path.isfile('./jsons/combos.csv'):
		print("DO NOT OVERWRITE combos.csv, takes forever to generate. Proceeding.")
		return

	write_object = open('./jsons/combos.csv', 'a+', newline = '')
	csv_writer = csv.writer(write_object)

	csv_writer.writerow(['hand', 'board'])

	print("---Generating hand board combos--- ")

	i = 0

	for board in board_field:
		# Ignore hands which duplicate the board (they are impossible)
		duplicates = set(board)
		for hand in hand_field:
			ignore_hand = False
			for card in hand:
				if card in duplicates:
					ignore_hand = True
					break
			if ignore_hand:
				continue # go to next hand

			## If you've reach this point, must be a valid hand/board combo! ##

			# Sort the number representations highest to lowest
			hand = sorted(hand, reverse = True)
			board = sorted(board, reverse = True)

			csv_writer.writerow([hand, board])
			
		i += 1
		if i % 1000 == 0:
			print("Boards completed: ", i)

def _map_integer_to_card(n):
	'''
	Maps an integer (or a list of integers) in range [0, 51] to a Card object
	Goes in order of rank, then suit (so all the 2's, then all the 3's, etc.)

	@n: an integer or list of integers in range [0, 51]
	'''
	if type(n) == list:
		result = []
		for num in n:
			assert num in range(52), "Error: integer to be mapped must be in range [0, 51]"
			r = int(num / 4) + 2 # converts ranks from [0, 12] to [2, 14]
			s = int(num % 4) + 1 # converts suits from [0, 3] to [1, 4]
			result.append(Card(r, s))
		return result
	else:
		r = int(n / 4) + 2
		s = int(n % 4) + 1
		return Card(r, s)

def _map_card_to_integer(c):
	'''
	Maps a Card object (or a list of Card objects) to an integer or list of integers in range [0, 51]

	@c: a Card object or list of Card objects
	'''
	if type(c) == list:
		result = []
		for card in c:
			rank = card.rank
			suit = card.suit

			num = (rank - 2) * 4
			num += (suit - 1)
			result.append(num)
		return result
	else:
		rank = c.rank
		suit = c.suit

		num = (rank - 2) * 4
		num += (suit - 1)

		return num

def generate_equity_points(combos_filepath):
	if os.path.isfile('./jsons/points.csv'):
		print("DO NOT OVERWRITE points.csv, takes forever to generate. Proceeding.")
		return

	# Need the RANGE_TO_HANDS_MAP.json
	range_to_hands = json.load(open('./jsons/RANGE_TO_HANDS_MAP.json', 'r'))

	i = 0

	points = pd.DataFrame()

	for combos in pd.read_csv(combos_filepath, header = 0, chunksize = 500000):
		# FLAG: EMERGENCY DATA THINNING TO MEET DEADLINE
		combos = combos.sample(frac = 0.1)

		print("Chunk: ", i)
		# Convert these to lists
		print("Converting to lists")
		combos['hand'] = combos.hand.apply(lambda x: [int(s) for s in x.strip('][').split(', ')])
		combos['board'] = combos.board.apply(lambda x: [int(s) for s in x.strip('][').split(', ')])

		# Convert these to strings
		print("Converting to strings")
		combos['hand'] = combos.hand.apply(lambda x: mechanics.convert_card_syntax(_map_integer_to_card(x)))
		combos['board'] = combos.board.apply(lambda x: mechanics.convert_card_syntax(_map_integer_to_card(x)))

		print("Calculating equities")
		p = pd.DataFrame()
		# For each hand/board combo, calculate equity of hand vs each of 8 ranges against the board to create an 8-D point. Add these 8-D points to a list)
		for j in range(8):
			# This line is a nested set of functions
			p['equity_%x' % j] = combos.apply(lambda row: int(100 * round(pbots_calc.calc(row['hand'] + ":" + ",".join(range_to_hands[str(j)]), row['board'], "", 100).ev[0], 2)), axis = 1)
		
		print("Writing")
		points.append(p)
		if i == 0:
			p.to_csv('./jsons/points.csv', mode = 'w', header = True)
		else:
			p.to_csv('./jsons/points.csv', mode = 'a', header = False)

		i += 1

def BUILD_ABSTRACTOR():
	# If file already exists, print message and do nothing
	if os.path.isfile('./jsons/centers.csv'):
		print("Hand abstraction map already exists, DO NOT OVERWRITE. If overwritten, you must regenerate the ENTIRE bot strategy.")
		return

	# Write hand/board combos to file
	generate_hand_board_combos(_generate_all_boards(), _generate_all_hands())

	# Calculate 8-D equities points from hand board combos
	generate_equity_points('./jsons/combos.csv')

	# Run k-means with k = 50 on these points
	print("Reading points.csv")
	points = pd.read_csv('./jsons/points.csv')
	points = points.sample(n = 3000000)
	print("Converting to matrix")
	points_matrix = np.matrix(points.values)

	print("Running K-means")
	kmeans = KMeans(n_clusters = 50, n_init = 1, max_iter = 100).fit(points_matrix)
	print("Writing to centers.csv")
	# Order by of equity distance from origin
	sorted_centers = sorted(kmeans.cluster_centers_, key = lambda x: distance.euclidean(x, np.asarray((0, 0, 0, 0, 0, 0, 0, 0))))
	centers_matrix = np.matrix(sorted_centers)
	centers = pd.DataFrame(centers_matrix)
	centers.to_csv('./jsons/centers.csv', index = False)



def setup():
	# Build and write the map for converting hands to ranges
	BUILD_RANGE_DICTIONARY()

	# Build and write the map for converting hand/board combos to centroids
	BUILD_ABSTRACTOR()

def test1():
	for i in range(52):
		c = _map_integer_to_card(i)
		print(c)
		x = _map_card_to_integer(c)
		print(x)

def test2():

	points = [
	[1, 4, 1],
	[1, 2, 2],
	[1, 4, 2],
	[2, 1, 2],
	[1, 1, 1],
	[2, 4, 2],
	[1, 1, 2],
	[2, 1, 1]
	]

	clusters, centroids = _k_means(points, 2)
	print(clusters)

def test3():
	range_to_hands = json.load(open('./jsons/RANGE_TO_HANDS_MAP.json', 'r'))

	combos = [
		['AdKs', 'TsJs4d'],
		['ThJd', 'TsJs4d'],
		['Qs8c', 'TsJs4d'],
		['Jc3d', 'TsJs4d']
	]

	points = []
	for combo in combos:
		equities = [None] * 8
		hand_str = combo[0]
		board_str = combo[1]
		for j in range(8):
			opp_hands = range_to_hands[str(j)]
			opp_hands_str = ",".join(opp_hands)
			equities[j] = int(100 * round(pbots_calc.calc(hand_str + ":" + opp_hands_str, board_str, "", 100000).ev[0], 2))
		points.append(equities)
	points_matrix = np.matrix(points)
	print(points_matrix)
	print(type(points_matrix))
	
	kmeans = KMeans(n_clusters = 2).fit(points_matrix)
	print(type(kmeans.cluster_centers_))

def run_k():
	print("Reading csv.")
	points = pd.read_csv('./jsons/points.csv')
	print("Converting to matrix")
	points_matrix = np.matrix(points.values)
	print("Running K-means")
	kmeans = KMeans(n_clusters = 100).fit(points_matrix)
	print(kmeans.cluster_centers_)
	centers_matrix = np.matrix(kmeans.cluster_centers_)

	centers = pd.DataFrame(centers_matrix)
	centers.to_csv('./jsons/centers.csv', index = False)



if __name__ == '__main__':
	setup()



