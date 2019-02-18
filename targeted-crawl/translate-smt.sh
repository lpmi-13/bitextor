#!/usr/bin/env bash

LANG1=$1
MOSES=$2
MOSES_MODEL=$3


cat /dev/stdin |
  $MOSES/scripts/tokenizer/tokenizer.perl -a -l $LANG1 |
  $MOSES/bin/moses2 -f $MOSES_MODEL --threads 16 -v 0 -search-algorithm 1 -cube-pruning-pop-limit 1000 |
  $MOSES/scripts/tokenizer/detokenizer.perl

