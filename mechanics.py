#!/usr/bin/python

import pbots_calc
import pokereval

import numpy
import random

from pokereval.card import Card
from copy import deepcopy

'''
Functions and classes to facilitate card mechanics and dealing
'''

# Definitions

HAND_SIZE = 2
FLOP_SIZE = 3
TURN_SIZE = 1
RIVER_SIZE = 1

def BUILD_DECK():
	"""
	Returns a deck of 52 cards in order of 2c-As

	@vals: corresponds 2-14 to 2-A
	@suits: correspond 1-4 to [s, h, d, c] # congruent to pokereval Card
	"""
	vals = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
	suits = [1, 2, 3, 4]
	deck = []

	for s in suits:
		for v in vals:
			deck.append(Card(v, s))
	return deck

class Deck(object):

	def __init__(self):
		self.deck = BUILD_DECK()
		random.shuffle(self.deck)

	def get_deck(self):
		"""
		Return a list of remaining cards in deck in order
		"""
		return self.deck

	def new_deck(self):
		"""
		Replaces current deck with a fresh new deck
		"""
		self.deck = BUILD_DECK()
		random.shuffle(self.deck)

	def deal_hand(self):
		"""
		Returns a list of HAND_SIZE cards from the deck, destructively decreasing deck size
		"""
		hand = []
		for _ in range(HAND_SIZE):
			hand.append(self.deck.pop(0))
		return hand

	def deal_flop(self):
		"""
		Returns a list of FLOP_SIZE cards from the deck, destructively decreasing deck size
		"""
		flop = []
		for _ in range(FLOP_SIZE):
			flop.append(self.deck.pop(0))
		return flop

	def deal_turn(self):
		"""
		Returns a list of TURN_SIZE cards from the deck, destructively decreasing deck size
		"""
		turn = []
		for _ in range(TURN_SIZE):
			turn.append(self.deck.pop(0))
		return turn

	def deal_river(self):
		"""
		Returns a list of RIVER_SIZE cards from the deck, destructively decreasing deck size
		"""
		river = []
		for _ in range(RIVER_SIZE):
			river.append(self.deck.pop(0))
		return river

def convert_card_syntax(cards):
	"""
	Returns a string representing the converted cards
	@ param cards: either a single Card object or a list of Card objects
	"""
	if type(cards) == list:
		cardStr = ""
		for c in cards:
			cardStr += (c.RANK_TO_STRING[c.rank] + c.SUIT_TO_STRING[c.suit])
		return cardStr
	else:
		return cards.RANK_TO_STRING[cards.rank] + cards.SUIT_TO_STRING[cards.suit]

def determine_winner(p0_hand, p1_hand, board):
	assert len(board) == FLOP_SIZE + TURN_SIZE + RIVER_SIZE, "Error: cannot determine winner on incomplete board"
	handStr = "%s:%s" % (convert_card_syntax(p0_hand), convert_card_syntax(p1_hand))
	boardStr = convert_card_syntax(board)

	res = pbots_calc.calc(handStr, boardStr, "", 1) # hand against board, no dead cards, 1 iteration
	if abs(res.ev[0] - 1.0) < 0.01:
		return 0 # player 0 wins
	elif abs(res.ev[1] - 1.0) < 0.01:
		return 1 # player 1 wins
	else:
		return 3 # represents a tie

def test_1():
	wins = [0, 0]

	for i in range(10000):
		deck = Deck()
		board = []
		board += (deck.deal_flop())
		board += (deck.deal_turn())
		board += (deck.deal_river())

		hands = []
		for _ in range(HAND_SIZE):
			hands.append(deck.deal_hand())
		handStrings = []
		for j in range(HAND_SIZE):
			handStr = ""
			handStr += convert_card_syntax(hands[j])
			handStrings.append(handStr)

		winner = determine_winner(hands[0], hands[1], board)
		if winner in [0, 1]:
			wins[winner] += 1

	for i in range(2):
		wins[i] /= 10000
	print(wins)

def test_2():
	testStr = "0~B:H,1~CL,"
	lst = testStr.split(',')
	lst = list(filter(None, lst))
	print(lst)

if __name__ == '__main__':
	test_1()	









