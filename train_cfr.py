#!/usr/bin/env

import abstractions
import mechanics

from cfr_helpers import *

import json
import numpy as np
import pandas as pd
import time

from random import random

def write_cumulative_regrets():
	with open('./cfr_data/cumulative_regrets.json', 'w') as f:
		json.dump(CUMULATIVE_REGRETS, f, indent = 1)

def write_cumulative_strategies():
	with open('./cfr_data/cumulative_strategies.json', 'w') as f:
		json.dump(CUMULATIVE_STRATEGIES, f, indent = 1)

def traverse(h, i, q):
	"""
	Basic recursive CFR traversal

	@h: a History object
	@i: an integer [0, 1] representing the current player
	@q: the sample probability of reaching this node in the game tree
	"""
	if h.is_terminal():
		p0_util, p1_util = h.compute_terminal_utilities()
		util = p0_util if i == 0 else p1_util
		return util / q
	elif h.is_chance():
		return traverse(h.perform_chance(), i, q)
	elif h.is_action():
		legal_actions = h.get_legal_actions()

		if h.active_player == (1 - i): # opponent's action
			I = h.convert_to_information_set(1 - i, HAND_ABSTRACTION_NODES, RANGE_MAP)
			sigma = _get_regret_matched_strategy(I, legal_actions)
			_update_cumulative_strategy(I, sigma, q)
			opp_action = select_action(sigma)
			assert opp_action in legal_actions, "Error: opponent chose illegal action for the history"
			new_history = h.perform_action(opp_action)
			return traverse(new_history, i, q)

		elif h.active_player == i:
			# For our action, use average strategy sampling to choose actions to explore
			I = h.convert_to_information_set(i, HAND_ABSTRACTION_NODES, RANGE_MAP)
			sigma = _get_regret_matched_strategy(I, legal_actions) # needed at end
			s = _get_cumulative_strategy(I, legal_actions)
			
			action_values = {} # dictionary to store counterfactual value of an action
			cumulative_strategy_sum = 0
			actions = s.keys()

			# Initialize all action values to 0 and calculate sum of cumulative strategy
			for a in actions:
				action_values[a] = 0
				cumulative_strategy_sum += s[a]

			# For each action, normalize and decide whether to sample
			for a in actions:
				# rho is probability an action gets sampled
				rho = max(EPSILON, ((BETA + s[a]) / (BETA + cumulative_strategy_sum)))
				if random() < rho: # select with rho probability
					new_history = h.perform_action(a)
					action_values[a] = traverse(new_history, i, q * min(1, rho))
			
			ev_sigma = 0 # expected value of the current strategy
			
			for a in actions:
				ev_sigma += sigma[a] * action_values[a]

			# Update cumulative regrets!
			for a in actions:
				CUMULATIVE_REGRETS[I][a] += (action_values[a] - ev_sigma) 

			global UPDATED_CR
			UPDATED_CR += 1

			return ev_sigma

		else:
			assert h.active_player == (1 - i), "Error: unexpected value for current player"
	else:
		assert False, "Error: unexpected node type in CFR tree"

def _get_cumulative_strategy(I, legal_actions):
	"""
	@I: information set
	@legal_actions: the legal performable actions for the history
	"""

	if I in CUMULATIVE_STRATEGIES:
		global REVISIT_CS
		REVISIT_CS += 1
		strategy = CUMULATIVE_STRATEGIES[I]
		assert len(legal_actions) == len(strategy), "Error: actions for strategy mismatched"
		return strategy
	else:
		strategy = {}
		for a in legal_actions:
			strategy[a] = 0 # initialize strategy sum to 0

		CUMULATIVE_STRATEGIES[I] = strategy
		return strategy

def _update_cumulative_strategy(I, action_map, q):
	"""
	@I: information set, a string
	@action_map: 
	@q: the legal performable actions for the history
	"""
	global UPDATED_CS
	UPDATED_CS += 1
	if I in CUMULATIVE_STRATEGIES:
		assert len(CUMULATIVE_STRATEGIES[I]) == len(action_map), "Error updating CS: actions for strategy mismatched"
		for action in action_map.keys():
			CUMULATIVE_STRATEGIES[I][action] += action_map[action] / q
	else:
		s = {}
		for action in action_map.keys():
			s[action] = action_map[action] / q
		CUMULATIVE_STRATEGIES[I] = s

def _get_cumulative_regrets(I, legal_actions):
	"""
	@I: information set
	@legal_actions: the legal performable actions for the history
	"""
	if I in CUMULATIVE_REGRETS:
		global REVISIT_CR
		REVISIT_CR += 1
		regrets = CUMULATIVE_REGRETS[I]
		return regrets
	else:
		regrets = {}
		for a in legal_actions:
			regrets[a] = 0 # initialize regrets to 0

		CUMULATIVE_REGRETS[I] = regrets
		return regrets


def _get_regret_matched_strategy(I, legal_actions):
	"""
	@I: information set
	@legal_actions: the legal performable actions for the history
	"""
	cumulative_regrets = _get_cumulative_regrets(I, legal_actions)

	# Sum non-negative regrets
	regret_sum = 0
	for regret in cumulative_regrets.values():
		if regret >= 0:
			regret_sum += regret
	
	assert regret_sum >=0, "error: summed regret incorrectly"
	# Get the strategy
	strategy = {}
	if regret_sum == 0:
		for a in legal_actions:
			strategy[a] = 1 / len(legal_actions)
	else:
		for a in legal_actions:
			if cumulative_regrets[a] > 0:
				strategy[a] = cumulative_regrets[a] / regret_sum
			else:
				strategy[a] = 0
	return strategy

def select_action(action_map):
	"""
	CITATION: This action selection code is adapted from action selection code in http://modelai.gettysburg.edu/2013/cfr/cfr.pdf
	"""
	action_sum = 0
	for prob in action_map.values():
		action_sum += prob

	r = random()
	cutoff = 0
	for action in action_map.keys():
		cutoff += action_map[action]
		if r <= cutoff:
			return action

def train_cfr():
	global CUMULATIVE_STRATEGIES, CUMULATIVE_REGRETS, EPSILON, BETA, UPDATED_CS, UPDATED_CR, REVISIT_CS, REVISIT_CR, HAND_ABSTRACTION_NODES, RANGE_MAP

	# Create list of arrays representing centroids
	try:
		centers = pd.read_csv('./jsons/centers.csv', header = 0)
		HAND_ABSTRACTION_NODES = centers.values
		RANGE_MAP = json.load(open('./jsons/RANGE_TO_HANDS_MAP.json', 'r'))
	except:
		assert False, "Error: you must run setup.py and create centroids csv before training. Exiting."

	try:
		print("---Loading cumulative strategies---")
		with open('./cfr_data/cumulative_strategies.json') as cr_file:
			CUMULATIVE_STRATEGIES = json.load(cr_file)
			print("Cumulative strategies loaded.")
	except:
		CUMULATIVE_STRATEGIES = {}
		print("Cumulative strategies file does not exist. Creating new map.")
	try:
		print("---Loading cumulative regrets---")
		with open('./cfr_data/cumulative_regrets.json') as cr_file:
			CUMULATIVE_REGRETS = json.load(cr_file)
			print("Cumulative regrets loaded.")
	except:
		CUMULATIVE_REGRETS = {}
		print("Cumulative regrets file does not exist. Creating new map.")


	EPSILON = 0.05
	BETA = 10 ** 6
	# These globals will log how many times we've updated and revisited regret and strategy maps
	REVISIT_CR = 0
	REVISIT_CS = 0
	UPDATED_CR = 0
	UPDATED_CS = 0

	path_count = 0 # will log how many times we've traversed a path in the game tree

	alternating_button = 1
	start_time = time.time()
	runtime = 28000 # Run CFR for 8 hours (21600 = 6 hours)

	while (time.time() - start_time) < runtime:
		deck = mechanics.Deck()
		start_history = History(alternating_button)

		strategy_ev = traverse(start_history, 0, 1.00)
		path_count += 1

		alternating_button = 1 - alternating_button # move the button

    	# Display information
		if path_count % 100 == 0:
			print("--------SUMMARY--------")
			print("Strategy sets:", len(CUMULATIVE_STRATEGIES))
			print("Regret sets:", len(CUMULATIVE_REGRETS))
			print("Updated regrets:", UPDATED_CR, "total times")
			print("Updated strategies:", UPDATED_CS, "total times")
			print("Revisited regrets:", REVISIT_CR, "total times")
			print("Revisited strategies:", REVISIT_CS, "total times")
			print("------------------------")

    	# Write to json every 100 traversals ()
		if path_count % 100 == 0:
			print("---Writing results to files---")
			write_cumulative_strategies()
			write_cumulative_regrets()
			print("----Wrote results to files----")

	print("----------ENDING----------")
	print("Ran for: ", time.time() - start_time, "seconds")


if __name__ == '__main__':
	train_cfr()








