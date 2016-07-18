#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys
import time
import csv
import argparse
import cPickle as pickle

import numpy as np
import pandas as pd
import tensorflow as tf

from utils import TextLoader
from model import Model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--save_dir', type=str, default='save',
                        help='model directory to store checkpointed models')
    parser.add_argument('--how', type=str, default='sample',
                        help='sample or text or accuracy, test one sample or test some samples compute accuracy of dataset')
    parser.add_argument('--sample_text', type=str, default=' ',
                        help='sample text')
    parser.add_argument('--test_dir', type=str, default='data',
                        help='data directory containing test.csv, necessary when how is test')
    parser.add_argument('--data_dir', type=str, default='data',
                        help='data directory containing input.csv, necessary when how is accuracy')

    args = parser.parse_args()
    if args.how == 'sample':
        sample(args)
    elif args.how == 'test':
        test(args)
    elif args.how == 'accuracy':
        accuracy(args)
    else:
        raise Exception('incorrect argument, input "sample" or "accuracy" after "--how"')


def transform(text, seq_length, vocab):
    x = map(vocab.get, text)
    x = map(lambda i: i if i else 0, x)
    if len(x) >= seq_length:
        x = x[:seq_length]
    else:
        x = x + [0] * (seq_length - len(x))
    return x


def sample(args):
    with open(os.path.join(args.save_dir, 'config.pkl'), 'rb') as f:
        saved_args = pickle.load(f)
    with open(os.path.join(args.save_dir, 'chars_vocab.pkl'), 'rb') as f:
        chars, vocab = pickle.load(f)
    with open(os.path.join(args.save_dir, 'labels.pkl'), 'rb') as f:
        labels = pickle.load(f)

    model = Model(saved_args, deterministic=True)
    x = transform(args.sample_text.decode('utf8'), saved_args.seq_length, vocab)

    with tf.Session() as sess:
        saver =tf.train.Saver(tf.all_variables())
        ckpt = tf.train.get_checkpoint_state(args.save_dir)
        if ckpt and ckpt.model_checkpoint_path:
            saver.restore(sess, ckpt.model_checkpoint_path)
            print model.predict(sess, labels, [x])


def test(args):
    with open(os.path.join(args.save_dir, 'config.pkl'), 'rb') as f:
        saved_args = pickle.load(f)
    with open(os.path.join(args.save_dir, 'chars_vocab.pkl'), 'rb') as f:
        chars, vocab = pickle.load(f)
    with open(os.path.join(args.save_dir, 'labels.pkl'), 'rb') as f:
        labels = pickle.load(f)

    model = Model(saved_args, deterministic=True)

    with open(args.test_dir+'/test.csv', 'r') as f:
        reader = csv.reader(f)
        texts = list(reader)

    texts = map(lambda i: i[0], texts)
    x = map(lambda i: transform(i.strip().decode('utf8'), saved_args.seq_length, vocab), texts)

    with tf.Session() as sess:
        saver =tf.train.Saver(tf.all_variables())
        ckpt = tf.train.get_checkpoint_state(args.save_dir)
        if ckpt and ckpt.model_checkpoint_path:
            saver.restore(sess, ckpt.model_checkpoint_path)

        start = time.time()
        results = model.predict(sess, labels, x)
        end = time.time()
        print 'prediction costs time: ', end - start

    with open(args.test_dir+'/result.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerows(zip(texts, results))


def accuracy(args):
    with open(os.path.join(args.save_dir, 'config.pkl'), 'rb') as f:
        saved_args = pickle.load(f)
    with open(os.path.join(args.save_dir, 'chars_vocab.pkl'), 'rb') as f:
        chars, vocab = pickle.load(f)
    with open(os.path.join(args.save_dir, 'labels.pkl'), 'rb') as f:
        labels = pickle.load(f)

    data_loader = TextLoader(args.data_dir, saved_args.batch_size, saved_args.seq_length)
    model = Model(saved_args, deterministic=True)

    with tf.Session() as sess:
        saver = tf.train.Saver(tf.all_variables())
        ckpt = tf.train.get_checkpoint_state(args.save_dir)
        if ckpt and ckpt.model_checkpoint_path:
            saver.restore(sess, ckpt.model_checkpoint_path)

        correct_total = 0.0
        num_total = 0.0
        data_loader.reset_batch_pointer()
        for b in range(data_loader.num_batches):
            start = time.time()
            state = model.initial_state.eval()
            x, y = data_loader.next_batch()
            feed = {model.input_data: x, model.targets: y, model.initial_state: state}
            sub_accuracy, correct_num, probs = sess.run([model.accuracy, model.correct_num, model.probs], feed_dict=feed)
            end = time.time()
            # print '{}/{}, accuracy = {:.3f}, time/batch = {:.3f}'\
            #     .format(b+1,
            #             data_loader.num_batches,
            #             sub_accuracy,
            #             end - start)

            # ############
            # if b==0:
            #     d1 = dict(zip(vocab.values(), vocab.keys()))
            #     d2 = dict(zip(labels.values(), labels.keys()))
            #     for n, i in enumerate(x):
            #         s = []
            #         for j in i:
            #             if j:
            #                 s.append(d1[j])
            #         print ''.join(s), '\t', d2[y[n]], '\t', y[n], '\t', np.argmax(probs[n], 0)
            # ############

            correct_total += correct_num
            num_total += saved_args.batch_size

        accuracy_total = correct_total / num_total
        print 'total_num = {}, total_accuracy = {:.6f}'.format(int(num_total), accuracy_total)



if __name__ == '__main__':
    main()

