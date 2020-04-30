#!/usr/bin/env

"""
PLEASE NOTE: setup.py MUST be run before using this file
"""

import mechanics

import numpy as np
import pandas as pd
from scipy.spatial import distance

import pbots_calc

HAND_SIZE = 2
FLOP_SIZE = 3
TURN_SIZE = 1
RIVER_SIZE = 1

def sort_cards(cards):
	"""
	Sorts a list of cards, first by rank, then by suit
	@ cards: a list of Card objects to be sorted

	Returns a sorted copy of the input list
	"""
	return sorted(cards, key = lambda x: (x.rank, x.suit), reverse = True)

def abstract_hand_preflop(hand):
	"""
	Abstracts a NLH hand to one of 169 hand buckets
	@hand: a List of exactly 2 Card objects

	Returns a string representing the abstracted hand. Can return 169 possible strings.
	"""
	assert len(hand) == 2, "Error: NLH hand must have exactly 2 cards"

	copy = sort_cards(hand) # order by rank

	ranks = [x.rank for x in copy]
	suits = [x.suit for x in copy]

	hand_str = ""
	for r in ranks:
		hand_str += copy[0].RANK_TO_STRING[r]
	if ranks[0] != ranks[1]: # if not a pocket pair
		if suits[0] == suits[1]:
			hand_str += "s" # suited hand
		else:
			hand_str += "o" # offsuit hand

	return hand_str


def abstract_hand_postflop(hand, board, nodes, range_to_hands):
	"""
	Abstracts a NLH hand to one of 100 hand buckets, depending on the board
	@hand: a List of exactly 2 Card objects
	@board: a List of 3, 4, or 5 Card objects
	@nodes: a list of arrays representing centroid coordinates to abstract to
	@range_to_hands: a dictinoary that maps a range [0, 7] to the corresponding list of hands in that range

	Returns a number [0, 99] representing the cluster index of abstraction
	"""
	assert len(hand) == 2, "Error in abstraction: incorrectly formatted hand length"
	assert len(board) in [3, 4, 5], "Error in abstraction: incorrectly formatted board length"

	# Get the sorted, string form of the hand
	sorted_cards = sort_cards(hand)
	hand_str = mechanics.convert_card_syntax(sorted_cards)
	
	# Abstract the board (i.e. sort the streets by rank then by suit).
	# Since we are using imperfect recall, we do not need to maintain distinction between streets.
	ordered_board = sorted(board, key = lambda c: (c.rank, c.suit))
	board_str = mechanics.convert_card_syntax(ordered_board)

	# Calculate equities to get 8_D point
	equities = [None] * 8
	for j in range(8):
		opp_hands = range_to_hands[str(j)]
		opp_hands_str = ",".join(opp_hands)
		equities[j] = int(100 * round(pbots_calc.calc(hand_str + ":" + opp_hands_str, board_str, "", 100000).ev[0], 2))
		
	equities = np.asarray(equities)

	def closest_node(node, nodes):
		nodes = np.asarray(nodes)
		dist_2 = np.sum((nodes - node)**2, axis=1)
		return np.argmin(dist_2)

	closest = closest_node(equities, nodes)
	
	return str(closest)

def test():
	deck = mechanics.Deck()
	hand = deck.deal_hand()
	board = deck.deal_flop()
	board += deck.deal_turn()

	centers = pd.read_csv('./jsons/centers.csv', header = 0)
	HAND_ABSTRACTION_NODES = centers.values

	print(hand)
	print(board)
	
	print(abstract_hand_postflop(hand, board, HAND_ABSTRACTION_NODES))


if __name__ == '__main__':
	test()
