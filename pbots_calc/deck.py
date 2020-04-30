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

	for s in suits:
		for v in vals:
			deck.append(Card(v, s))
	return deck

class Dealer(object):

	def __init__(self):
		self.deck = BUILD_DECK()
		random.shuffle(self.deck)

	def getDeck(self):
		"""
		Return a list of remaining cards in deck in order
		"""
		return self.deck

	def newDeck(self):
		"""
		Replaces current deck with a fresh new deck
		"""
		self.deck = BUILD_DECK()
		random.shuffle(self.deck)

	def dealHand(self):
		"""
		Returns a list of HAND_SIZE cards from the deck, destructively decreasing deck size
		"""
		hand = []
		for _ in range(HAND_SIZE):
			hand.append(self.deck.pop(0))
		return hand

	def dealFlop(self):
		flop = []
		for _ in range(FLOP_SIZE):
			flop.append(self.deck.pop(0))
		return flop

	def dealTurn(self):
		turn = []
		for _ in range(FLOP_SIZE):
			turn.append(self.deck.pop(0))
		return turn

	def dealRiver(self):
		river = []
		for _ in range(FLOP_SIZE):
			river.append(self.deck.pop(0))
		return river

def convertCardSyntax(cards):
	"""
	Returns a string representing the converted cards
	@ param cards: either a single Card object or a list of Card objects
	"""
	if type(cards) == list:
        cardstr = ""
        for c in cards:
            cardstr+=(c.RANK_TO_STRING[c.rank]+c.SUIT_TO_STRING[c.suit])
        return cardstr
    else:
        return cards.RANK_TO_STRING[cards.rank]+cards.SUIT_TO_STRING[cards.suit]


def determineWinner(p0_hand, p1_hand, board):
	assert len(board) == FLOP_SIZE + TURN_SIZE + RIVER_SIZE, "Error: cannot determine winner on incomplete board"
	handStr = "%s:%s" % (convertCardSyntax(p0_hand), convertCardSyntax(p1_hand))
	boardStr = convertCardSyntax(board)

	resultObj = calc(handStr, boardStr, "", 1)
	if abs(res.ev[0] - 1.0) < 0.01:
        return 0 # player 0 wins
    elif abs(res.ev[1] - 1.0) < 0.01:
        return 1 # player 1 wins
    else:
    	return 3 # represents a tie
	
def test():
	board = ""
	dead = ""
	r = pbots_calc.calc("4qo:jts+", "", "", 1000000)
	if r:
		print(list(zip(r.hands, r.ev)))

if __name__ == '__main__':
	test()	









