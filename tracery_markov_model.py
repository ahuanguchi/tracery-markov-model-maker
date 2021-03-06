import argparse
import json
import os
from collections import defaultdict
from functools import reduce
from itertools import chain

try:
    from math import gcd
except ImportError:
    from fractions import gcd

PUNCTUATION = {
    '0PUNC_EL': '...',
    'PUNC_PER': '.',
    'PUNC_QMK': '?',
    'PUNC_EPT': '!',
    'PUNC_COM': ',',
    'PUNC_COL': ':',
    'PUNC_SEM': ';',
}

ENDINGS = {'PUNC_PER', 'PUNC_QMK', 'PUNC_EPT'}


def _get_spaces(tokens):
    num_tokens = len(tokens)
    return ('' if i + 1 == num_tokens or tokens[i+1][:8] in PUNCTUATION else ' '
            for i in range(num_tokens))


def _substitute_word_origin(tokens):
    return (x if x != 'origin' else 'WORD_ORIGIN' for x in tokens)


def _symbol(tokens):
    spaces = _get_spaces(tokens)
    tokens = _substitute_word_origin(tokens)
    return '#{}#'.format(''.join(chain.from_iterable(zip(tokens, spaces))))


def _literal(tokens, convert_substitutes=False):
    spaces = _get_spaces(tokens)
    if not convert_substitutes:
        tokens = _substitute_word_origin(tokens)
    joined = ''.join(chain.from_iterable(zip(tokens, spaces)))
    if convert_substitutes:
        for k, v in PUNCTUATION.items():
            joined = joined.replace(k, v)
    return joined


def _ngram(tokens):
    if tokens[1][:8] in PUNCTUATION:
        space = ''
    else:
        space = ' '
    return '{}{}{}'.format(_literal(tokens[:1], True), space, _symbol(tokens[1:]))


def _gcd_of_seq(numbers):
    if len(numbers) == 1:
        return next(iter(numbers))
    return reduce(lambda x, y: gcd(x, y), numbers)


def corpus_to_tracery_json(corpus_path, ngram_size=3, all_lowercase=False):
    tracery_dict = defaultdict(list)
    tracery_dict['origin'].append(_symbol(['start_boundary']))
    
    with open(corpus_path) as f:
        for line in f:
            line = line.strip()
            if all_lowercase:
                line = line.lower()
            for k, v in sorted(PUNCTUATION.items()):
                line = line.replace(v, ' ' + k)
            line = line.split()
            limit = len(line) - ngram_size + 1
            for i in range(limit):
                rule_tokens = line[i:i+ngram_size-1]
                if i == 0 or line[i-1] in ENDINGS and line[i] not in PUNCTUATION:
                    tracery_dict['start_boundary'].append(_symbol(rule_tokens))
                tracery_dict[_literal(rule_tokens)].append(_ngram(line[i:i+ngram_size]))
            rule_tokens = line[-ngram_size+1:]
            tracery_dict[_literal(rule_tokens)].append(_literal(rule_tokens, True))
    
    for rule, options in tracery_dict.items():
        if len(options) > 1:
            counts = defaultdict(int)
            for option in options:
                counts[option] += 1
            counts_gcd = _gcd_of_seq(counts.values())
            new_options = []
            for option in counts:
                new_options.extend([option] * int(counts[option] / counts_gcd))
            tracery_dict[rule] = new_options
    
    if not os.path.exists('output'):
        os.mkdir('output')
    output_fname = os.path.basename(corpus_path).rsplit('.', 1)[0] + '.json'
    with open(os.path.join('output', output_fname), 'w') as f:
        f.write(json.dumps(tracery_dict))
        f.write('\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('corpus')
    parser.add_argument('-n', '--ngram', type=int, default=3,
                        help='n-gram size (default: %(default)s)')
    parser.add_argument('-l', '--lowercase', action='store_true',
                        help='convert all input to lowercase')
    args = parser.parse_args()
    if args.ngram < 2:
        parser.error('Size of n-gram must be at least 2')
    corpus_to_tracery_json(args.corpus, args.ngram, args.lowercase)
