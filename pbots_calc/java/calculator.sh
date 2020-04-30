#!/bin/sh
export DYLD_LIBRARY_PATH=/Users/nick.zhang/Documents/senior_project/poker_bot/pbots_calc/export/darwin/lib:$LD_LIBRARY_PATH
java -cp /Users/nick.zhang/Documents/senior_project/poker_bot/pbots_calc/java/jnaerator-0.11-SNAPSHOT-20121008.jar:/Users/nick.zhang/Documents/senior_project/poker_bot/pbots_calc/java/bin pbots_calc.Calculator $@