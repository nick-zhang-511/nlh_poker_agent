#!/usr/bin/env

import abstractions
import mechanics

# Need these for testing but not for functionality
import json
import numpy as np
import time

from copy import deepcopy

# TODO: Need to map weird bet sizes to the bet outcomes used in our InfoSet
# Note: Best way to do this is just to map bet size to nearest bet size?
# (fuck this is bad though because stack sizes wont be consistent anymore)
# can just map stack size and bet size to nearest stack/bet combo and take strategy from that infoset

STARTING_STACK = 200
BB_AMT = 2
SB_AMT = 1

class History(object):
	"""
	A History object represents a game history
	It holds the following parameters.
	@ history: a string encoding the ACTIONS taken so far
	@ node_type: a value in [0, 1, 2] representing chance, action, terminal
	@ round: the value representing the betting round [0, 1, 2]. 0 means no bet yet. (max 2 betting rounds)
	@ street: a value in [0, 1, 2, 3] representing preflop, flop, turn, river
	@ button: a value in [0, 1] representing the player holding the button
	@ deck: a Deck object
	@ board: a list of Cards representing the current board
	@ active_player: the player whose turn it is to act
	@ pot: a number representing how many chips are in the pot
	@ hands: a list of size 2 of lists of Cards, representing player hands
	@ stacks: a list of size 2 representing stacks of p0 and p1 respectively
	@ contributions: a list of size 2 representing contributions to the CURRENT BETTING ROUND of p0 and p1 respectively
	"""
	# Comprehensive Constructor (allows all instance variables)
	def __init__(self, btn, hist = "", ntype = 0, rnd = 0, strt = 0, deck = mechanics.Deck(), brd = [], \
				act_pl = None, pot = 0, hands = [None, None], stacks = [STARTING_STACK, STARTING_STACK], \
				contributions = [0, 0]):

		assert len(stacks) == 2 and len(contributions) == 2, "Error: must be two stacks"
		self.history = hist
		self.node_type = ntype
		self.round = rnd
		self.street = strt
		self.button = btn
		self.deck = deck
		self.board = brd
		self.active_player = btn if act_pl == None else act_pl
		self.pot = pot
		self.hands = hands
		self.stacks = stacks
		self.contributions = contributions

	def convert_to_information_set(self, player, abstraction_nodes, range_map):
		"""
		Parameters
		@ history: a history object
		@ player: the players from whose POV the InfoSet is calculated

		Returns a string that encodes the information set
		"""

		"""
		Format:
		Hand Bucket (private info) (abstracted)
		Board

		^ These two are combined through the hand abstraction
		
		Street (since the board is abstracted)
		Position/Button (from perspective of player)
		Betting round (TODO: do we need this? or is it encoded into the actions string)
		Pot
		Stack sizes (self first, opponent second)
		Contributions (self first, opponent second)
		Actions taken so far
		"""

		'''
		NOTE: This should take into account
		Hand abstractions
		Imperfect Recall
		Pot abstractions
		Betting abstractions
		'''
		board = self.board

		# Abstract hand
		if (len(board) == 0): # preflop abstraction
			hand_board = abstractions.abstract_hand_preflop(self.hands[player])
		else: # postflop abstraction
			hand_board = abstractions.abstract_hand_postflop(self.hands[player], self.board, abstraction_nodes, range_map)

		street = str(self.street)
		position = str(1) if self.button == player else str(0)
		pot = str(self.pot)
		stack_sizes = str(self.stacks[player]) + ', ' + str(self.stacks[1 - player])
		contributions = str(self.contributions[player]) + ', ' + str(self.contributions[1 - player])

		# Nicely format actions
		player_actions = self.history.split(',')
		player_actions = list(filter(None, player_actions)) # remove empty strings after split
		actions = ",".join(player_actions)

		return "H:" + hand_board + ",S:" + street + ",D:" + position + ", INFO:" + pot + "," + stack_sizes + "," + contributions + "," + actions

	def is_chance(self):
		return self.node_type == 0

	def is_action(self):
		return self.node_type == 1

	def is_terminal(self):
		return self.node_type == 2

	def get_legal_actions(self):
		"""
		Gets the legal actions for the active player at this history
		** DOES NOT MODIFY THIS HISTORY **
		"""
		# Error searching
		assert self.node_type == 1, "Error: can only get actions for action node"
		assert len(self.stacks) == 2, "a"
		assert len(self.contributions) == 2, "b"
		assert sum(self.stacks) + self.pot == 2 * STARTING_STACK, "c"
		assert len(self.board) <= 5, "d"
		assert self.street in [0, 1, 2, 3], "e"

		prevBet = abs(self.contributions[0] - self.contributions[1])
		if self.round > 0:
			assert prevBet > 0, "Error: previous bet must have been greater than 0 to have gotten to nonzero betting round"

		if 0 in self.stacks: # if either player is all in
			if self.stacks[self.active_player] == 0: # if active player is all-in
				# active player can only check
				return ["CK"]
			else: # only the opponent is all-in
				if prevBet > 0: # if they bet an amount
					# can fold or call the all-in
					return ["F", "CL"]
				else: # no prev bet, so can check (they are all in)
					return ["CK"]

		if self.round == 2: # 2 betting rounds already, must fold or call
			assert prevBet > 0, "Error: to get to last betting round, last bet must be positive"
			return ["F", "CL"]
		else:
			if prevBet > 0:
				actions = ["F", "CL", "R:P", "R:A"] # can fold, call, raise
			else: # no last bet
				actions = ["CK", "B:H", "B:P", "B:A"] # can check or bet

			# remove non-all-in bets that would pot commit us
			# halfPot = self.pot / 2
			# if (self.stacks[0] < (halfPot / 0.6) or self.stacks[1] < (halfPot / 0.6)):
			# 	for a in ["B:H", "B:P", "R:P"]:
			# 		if a in actions:
			# 			actions.remove(a)
			return actions

	def perform_action(self, action):
		"""
		Returns the new history after the provided action
		** DOES NOT MODIFY THIS HISTORY **
		"""
		assert self.node_type == 1, "Error: cannot perform action on non-action node"
		history = deepcopy(self) # copy the current history to modify into new history

		# Handle street, node types, stack sizes + contributions, and betting rounds here
		# Active player changes, street resets, and string updates handled at end of method
		if action == "F":
			history.node_type = 2 # convert history to terminal
		elif action == "CK":
			if self.street == 0: # preflop
				if self.active_player != self.button: # BB checks
					# Advance the street
					history.street += 1
					history.node_type = 0 # chance node now (flop must be dealt)
				else:
					assert False, "Error: small blind can never check preflop"
			else: # postflop
				if self.active_player == self.button: # Button checked back
					# closing check
					history.street += 1
					history.node_type = 2 if self.street == 3 else 0
				else:
					pass # move to next player

		elif action == "CL":
			if self.street == 0: # preflop call
				if self.active_player == self.button: # SB called
					if self.round > 0: # SB called without limping
						# action is over
						history.street += 1
						history.node_type = 0
					else: # SB limped
						# BB has an action this street
						history.node_type = 1
				else: # BB called
					history.street += 1
					history.node_type = 0
			else: # postflop call
				history.street += 1
				history.node_type = 2 if self.street == 3 else 0

			# handle call mechanics
			prevBet = abs(self.contributions[0] - self.contributions[1]) # this is the amount needed to call
			assert self.contributions[self.active_player] < self.contributions[1 - self.active_player], "Error: player calling but does not have less in the pot"
			
			history.stacks[self.active_player] -= prevBet # subtract call from stack
			history.contributions[self.active_player] += prevBet # add call to contribution
			history.pot += prevBet
			assert history.contributions[0] == history.contributions[1], "Error: contributions must be the same after a call"

		else: # action = Bet or Raise
			parsedAction = action.split(':')
			assert len(parsedAction) == 2, "Error: parsed action formatted wrong (too many pieces)"
			category = parsedAction[0]
			amount = parsedAction[1]
			# bounds on bets/raises
			prevBet = abs(self.contributions[0] - self.contributions[1])
			minBet = max(2, prevBet) # must bet at least a BB, and must raise by at least last bet amount
			'''
			Maximum bet is complicated
			Cannot bet more than your own stack
			Also, cannot bet more than (opponents stack + prevBet)
			'''
			opponent = 1 - self.active_player
			maxBet = min(self.stacks[self.active_player], self.stacks[opponent] + prevBet)
			assert maxBet >= minBet, "Error: max bet can't be less than min bet"

			if amount == 'H': # half pot bet
				halfPot = self.pot / 2
				betAmount = min(max(minBet, halfPot), maxBet)
			elif amount == 'P':
				fullPot = self.pot
				betAmount = self.pot + 2 * prevBet # to give at best 2:1 odds
				betAmount = min(max(minBet, betAmount), maxBet)
			elif amount == 'A':
				betAmount = maxBet # all-ins handled this way
			else:
				assert False, "Error: active player gave illegal bet/raise amount"

			if category == 'B':
				assert self.contributions[0] == self.contributions[1], "Error: If betting, both players must have same contribution"
				if (self.street > 0):
					assert self.contributions[0] == self.contributions[1] == 0, "Error: If betting postflop, both players must have 0 contribution"
				# handle bet mechanics
				history.stacks[self.active_player] -= betAmount # subtract call from stack
				history.contributions[self.active_player] += betAmount # add call to contribution
				history.pot += betAmount
			elif category == 'R':
				# handle raise mechanics
				history.stacks[self.active_player] -= betAmount # subtract raise from stack
				history.contributions[self.active_player] += betAmount # add raise to contribution
				history.pot += betAmount
			else:
				assert False, "Error: active player gave illegal action category"

			# advance the betting round
			history.round += 1
			assert history.round <= 2, "Error: betting round shouldn't have been able to go past 2"


		if history.street > self.street: # if we advance a street
			history.contributions = [0, 0] # reset contributions
			history.round = 0 # reset to new betting round
			history.active_player = 1 - self.button # should always be OOP player
		else:
			history.active_player = 1 - self.active_player # should be opposite player

		# best idea to only encode actions into the history string
		history.history = self.history + ("%s~%s," % (str(self.active_player), action)) # append player action to prev history

		return history

	def perform_chance(self):
		"""
		Returns new history after performing chance automatically for flop, turn, and river
		** DOES NOT MODIFY THIS HISTORY **
		"""
		assert self.node_type == 0, "Error: cannot perform chance on non-chance node"
		history = deepcopy(self)

		if self.street == 0: # now preflop
			# deal hands
			# bucket hands as well
			for i in range(2): # deal to both players
				history.hands[i] = history.deck.deal_hand()
			history.round = 0

			# put in the blinds
			button = self.button
			bb = 1 - button

			history.stacks[button] -= SB_AMT # button pays SB
			history.contributions[button] += SB_AMT
			history.stacks[bb] -= BB_AMT
			history.contributions[bb] += BB_AMT
			history.pot = BB_AMT + SB_AMT

		elif self.street == 1: # now flop
			# deal flop
			history.board += history.deck.deal_flop()
		elif self.street == 2: # now turn
			# deal turn
			history.board += history.deck.deal_turn()
		elif self.street == 3: # now river
			# deal river
			history.board += history.deck.deal_river()
		else:
			assert False, "Error: street took on impossible value"

		history.node_type = 1 # chance nodes are always followed by action nodes

		return history

	def compute_terminal_utilities(self):
		"""
		Returns a tuple (p0_payout, p1_payout) where
		p0_payout is the utility (PnL) of player 0
		p1_payout is the utility (PnL) of player 1
		**DOES NOT MODIFY THIS HISTORY**
		"""
		assert(self.node_type == 2), "Error: node type must be terminal to compute terminal utilities"
		playerActions = self.history.split(',')
		playerActions = list(filter(None, playerActions)) # remove empty strings after split
		lastPlayerAction = playerActions[-1].split('~') # last player action pair (format = [PLAYER_STR, ACTION_STR])

		assert len(lastPlayerAction) == 2, "Error: (player, action) pair incorrectly formatted"
		assert lastPlayerAction[1] in ['CK', 'CL', 'F'], "Error: reached terminal node in unexpected way"

		if lastPlayerAction[1] == 'F':
			folder = int(lastPlayerAction[0]) # folding player
			winner = 1 - folder # winning player
			assert self.stacks[folder] != self.stacks[winner], "Error: Fold must imply unequal stacks"
			assert sum(self.stacks) + self.pot == 2 * STARTING_STACK

			# Winner goes + (the pot minus winner's last contribution to the pot)
			potBeforeBet = (self.pot - self.contributions[winner])
			winUtility = potBeforeBet / 2
			loseUtility = -1 * winUtility

			if winner == 0:
				return (winUtility, loseUtility)
			else:
				return (loseUtility, winUtility)

		elif self.street == 4: # reached river
			assert len(self.board) == 5, "Error: must have complete board to compute terminal utilities"

			winner = mechanics.determine_winner(self.hands[0], self.hands[1], self.board)

			winUtility = self.pot / 2
			loseUtility = -1 * winUtility

			if winner == 0:
				return (winUtility, loseUtility)
			else:
				return (loseUtility, winUtility)

		else:
			assert False, "Error: reached terminal node in unexpected way"


def testHistories():
	start = time.time()
	iters = 1
	for i in range(iters):
		newHistory = History(btn = 0)

		history = deepcopy(newHistory)
		while history.node_type != 2:
			if history.node_type == 0: # chance node
				history = history.perform_chance()
			elif history.node_type == 1: # action node
				legalActions = history.get_legal_actions()
				action = np.random.choice(legalActions)
				history = history.perform_action(action)
				print("Action:", action)
				print("InfoSet:", history.convert_to_information_set(0))
			else:
				assert False, "ERROR: unexpected node type"
		print(history.history)
	end = time.time()
	dur = end - start
	print("Hands per second:", iters / dur) # hands per second



if __name__ == '__main__':
	testHistories()






