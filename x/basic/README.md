# Basic translation

From: [Computer Recreations - Markov Chainer - Scientific American](https://archive.org/details/ComputerRecreationsMarkovChainer/page/n1/mode/2up) (1988)

The trick is to apply Shannon's algorithm for Markov chains but with entire
words instead of characters as the concatenated symbols. As mark ■V. shaney
scans a text, it builds a frequency table for all words that follow all the
word pairs in the text. The program then proceeds to babble probabilistically
on the basis of the word frequencies.

A key feature of the program is that . it regards any punctuation adjacent to a
word as part of the word. That feature enables it to form sentences having a
beginning and an end. Approximately half of them are even grammatical. I
shudder to think what the V program might produce after scanI ning this
article!
