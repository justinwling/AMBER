# Author: Evan M. Cofer
# Created on June 5, 2020
"""
This module provides the `BioIntervalSource` class and its children.
These are essentially wrappers for sets of sequence intervals and
associated labels.
"""
#import keras
import tensorflow as tf
import numpy
from .sequences import EncodedHDF5Genome


class BioIntervalSource(object):
    """A generic class for labeled examples of biological intervals.
    The amount of padding added to the end of the intervals is able to
    be changed during runtime. This allows these functions to be passed
    to objects such as a model controller.

    Parameters
    ----------
    example_file : str
        A path to a file that contains the examples in BED-like format.
        Specifically, this file will have one example per line, with
        the chromosome, start, end, and label for the example. Each
        column is separated by tabs.
    reference_sequence : Sequence
        The reference sequence used to generate the input sequences
        from the example coordinates.
    seed : int, optional
        Default is `1337`. The value used to seed random number generation.
    n_examples : int, optional
        Default is `None`. The number of examples. If left as `None`, will
        use all of the examples in the file. If fewer than `n_examples`
        are found, and error will be thrown.

    Attributes
    ----------
    reference_sequence : Sequence
        The reference sequence used to generate the input sequences
        from the example coordinates.
    examples : list
        A list of the example coordinates.
    labels : list
        A list of the labels for the examples.
    left_pad : int
        The length of padding added to the left side of the interval.
    right_pad : int
        The length of padding added to the right side of the interval.
    random_state : numpy.random.RandomState
        A random number generator to use.
    seed : int
        The value used to seed the random number generator.
    """
    def __init__(self, example_file, reference_sequence, n_examples=None, seed=1337, pad=400):
        if type(reference_sequence) is str:
            self.reference_sequence = EncodedHDF5Genome(input_path=reference_sequence, in_memory=False)
        else:
            self.reference_sequence = reference_sequence
        self.left_pad = 0
        self.right_pad = 0

        # Setup RNG.
        self.seed = seed
        self.random_state = numpy.random.RandomState(seed=self.seed)

        # Load examples.
        self.labels = list()
        self.examples = list()
        with open(example_file, "r") as read_file:
            for line in read_file:
                line = line.strip()
                if not line.startswith("#"):
                    if line:
                        line = line.split("\t")
                        chrom, start, end, strand = line[:4]
                        label = [int(x) for x in line[4:]]
                        self.labels.append(numpy.array(label))
                        self.examples.append((chrom, int(start), int(end), strand))
        # TODO: Consider using separate random states for index shuffling and this part?
        if n_examples is not None:
            if len(self.examples) < n_examples:
                s = ("Specified value of examples was {}".format(n_examples) +
                     ", but only {} were found in \"{}\".".format(len(self.examples),
                                                                  example_file))
                raise RuntimeError(s)
            elif len(self.examples) > n_examples:
                idx = self.random_state.choice(len(self.examples),
                                               n_examples,
                                               replace=False)
                idx.sort()
                self.examples = numpy.array(self.examples, dtype='O')[idx].tolist()
                self.labels = numpy.array(self.labels, dtype='O')[idx].tolist()
                self.labels = [numpy.array(x) for x in self.labels]
            else:
                # Ensure random state not affected by using input with length of n_examples.
                idx = self.random_state.choice(2, 1, replace=False)
                del idx
        else: # Ensure random state not affected by not using n_examples.
            idx = self.random.state.choice(2, 1, replace=False)
            del idx

        self.set_pad(pad)

    def padding_is_valid(self, value):
        """Determine if the specified value is a valid value for padding
        intervals.

        Parameters
        ----------
        value : int
            Proposed amount of padding.

        Returns
        -------
        bool
            Whether the input value is valid.
        """
        if value < 0:
            return False
        else:
            return True

    def _test_padding(self, value):
        """Tests if padding is valid or not. If invalid, raises an error.


        Parameters
        ----------
        value : int
            Amount of padding to test.

        Returns
        -------
        None

        Raises
        ------
        ValueError
            This method throws an error if the proposed amount of padding is
            not a valid amount.
        """
        if not self.padding_is_valid(value):
            s = "Invalid padding amount : {}".format(value)
            raise ValueError(s)

    def set_left_pad(self, value):
        """Sets the length of the padding added to the left
        side of the input sequence.

        Parameters
        ----------
        value : int
            The length of the padding to add to the left side of an example
            interval.
        """
        self._test_padding(value)
        self.left_pad = value

    def set_right_pad(self, value):
        """Sets the length of the padding added to the right side of an
        example interval.


        Parameters
        ----------
        value : int
            The length of the padding to add to the right side of an example
            interval.
        """
        self._test_padding(value)
        self.right_pad = value

    def set_pad(self, value):
        """Sets the length of padding added to both the left and right sides of
        example intervals.

        Parameters
        ----------
        value : int
            The length of the padding to add to the left and right sides of
            input example intervals.
        """
        self._test_padding(value)
        self.left_pad = value
        self.right_pad = value

    def __len__(self):
        """Number of examples available.

        Returns
        -------
        int
            The number of examples available.
        """
        return len(self.examples)

    def _load_unshuffled(self, item):
        """Loads example `item` from the unshuffled list of examples.

        Parameters
        ----------
        item : int
            The index of the example to load.

        Returns
        -------
        tuple(numpy.ndarray, numpy.ndarray)
        """
        chrom, start, end, strand = self.examples[item]
        x = self.reference_sequence.get_sequence_from_coords(chrom, start - self.left_pad, end + self.right_pad, strand)
        y = self.labels[item]
        return x, y


class BioIntervalSequence(BioIntervalSource, tf.keras.utils.Sequence):
    """This data sequence type holds intervals in a genome and a
    label associated with each interval. Unlike a generator, this
    is based off of `keras.utils.Sequence`, which shifts things like
    shuffling elsewhere. The amount of padding added to the end of
    the intervals is able to be changed during runtime. This allows
    these functions to be passed to objects such as a model
    controller.

    Parameters
    ----------
    example_file : str
        A path to a file that contains the examples in BED-like format.
        Specifically, this file will have one example per line, with
        the chromosome, start, end, and label for the example. Each
        column is separated by tabs.
    reference_sequence : Sequence
        The reference sequence used to generate the input sequences
        from the example coordinates.
    n_examples : int, optional
        Default is `None`. The number of examples. If left as `None`, will
        use all of the examples in the file. If fewer than `n_examples` are
        found, an error will be thrown.
    seed : int, optional
        Default is `1337`. The value used to seed random number generation.

    Attributes
    ----------
    reference_sequence : Sequence
        The reference sequence used to generate the input sequences
        from the example coordinates.
    examples : list
        A list of the example coordinates.
    labels : list
        A list of the labels for the examples.
    left_pad : int
        The length of padding added to the left side of the interval.
    right_pad : int
        The length of padding added to the right side of the interval.
    random_state : numpy.random.RandomState
        A random number generator to use.
    seed : int
        The value used to seed the random number generator.
    """
    def __init__(self, example_file, reference_sequence, n_examples=None, seed=1337):
        super(BioIntervalSequence, self).__init__(
            example_file=example_file,
            reference_sequence=reference_sequence,
            n_examples=n_examples, seed=seed)

    def __getitem__(self, item):
        """
        Indexes into the set of examples and labels.

        Parameters
        ----------
        item : int
            The index in the example/label pairs to fetch.

        Returns
        -------
        tuple(numpy.ndarray, numpy.ndarray)
            A tuple consisting of the example and the target label.

        """
        return self._load_unshuffled(item)


class BioIntervalGenerator(BioIntervalSource):
    """This data generator type holds intervals in a genome and a
    label associated with each interval. This essentially acts as
    an iterator over the inputs examples. This approach is useful
    and preferable to `BioIntervalSequence` when there are a very
    large number of examples in the input. The amount of padding
    added to the end of the intervals is able to be changed during
    runtime. This allows these functions to be passed to objects
    such as a model controller.

    Parameters
    ----------
    example_file : str
        A path to a file that contains the examples in BED-like format.
        Specifically, this file will have one example per line, with
        the chromosome, start, end, and label for the example. Each
        column is separated by tabs.
    reference_sequence : Sequence
        The reference sequence used to generate the input sequences
        from the example coordinates.
    n_examples : int, optional
        Default is `None`. The number of examples. If left as `None`, will
        use all of the examples in the file. If fewer than `n_examples` are
        found, an error will be thrown.
    seed : int, optional
        Default is `1337`. The value used to seed random number generation.

    Attributes
    ----------
    reference_sequence : Sequence
        The reference sequence used to generate the input sequences
        from the example coordinates.
    examples : list
        A list of the example coordinates.
    labels : list
        A list of the labels for the examples.
    left_pad : int
        The length of padding added to the left side of the interval.
    right_pad : int
        The length of padding added to the right side of the interval.
    random_state : numpy.random.RandomState
        A random number generator to use.
    seed : int
        The value used to seed random number generation.

    """
    def __init__(self, example_file, reference_sequence, n_examples=None, seed=1337):
        super(BioIntervalGenerator, self).__init__(
            example_file=example_file,
            reference_sequence=reference_sequence,
            n_examples=n_examples,
            seed=seed)
        raise NotImplementedError


class BatchedBioIntervalSequence(BioIntervalSource, tf.keras.utils.Sequence):
    """This data sequence type holds intervals in a genome and a
    label associated with each interval. Unlike a generator, this
    is based off of `keras.utils.Sequence`, which shifts things like
    shuffling elsewhere. The amount of padding added to the end of
    the intervals is able to be changed during runtime. This allows
    these functions to be passed to objects such as a model
    controller. Examples are divided into batches.

    Parameters
    ----------
    example_file : str
        A path to a file that contains the examples in BED-like format.
        Specifically, this file will have one example per line, with
        the chromosome, start, end, and label for the example. Each
        column is separated by tabs.
    reference_sequence : Sequence or str
        The reference sequence used to generate the input sequences
        from the example coordinates; could be a Sequence instance or a 
        filepath to reference sequence.
    batch_size : int
        Specifies size of the mini-batches.
    shuffle : bool
        Specifies whether to shuffle the mini-batches.
    n_examples : int, optional
        Default is `None`. The number of examples. If left as `None`, will
        use all of the examples in the file. If fewer than `n_examples` are
        found, an error will be thrown.
    seed : int, optional
        Default is `1337`. The value used to seed random number generation.

    Attributes
    ----------
    reference_sequence : Sequence
        The reference sequence used to generate the input sequences
        from the example coordinates.
    examples : list
        A list of the example coordinates.
    labels : list
        A list of the labels for the examples.
    left_pad : int
        The length of padding added to the left side of the interval.
    right_pad : int
        The length of padding added to the right side of the interval.
    batch_size : int
        Specifies size of the mini-batches.
    shuffle : bool
        Specifies whether to shuffle the mini-batches.
    random_state : numpy.random.RandomState
        A random number generator to use.
    seed : int
        The value used to seed the random number generator.
    """
    def __init__(self, example_file, reference_sequence,
                 batch_size, shuffle=True, n_examples=None, seed=1337, pad=0):
        super(BatchedBioIntervalSequence, self).__init__(
            example_file=example_file,
            reference_sequence=reference_sequence,
            n_examples=n_examples,
            seed=seed,
            pad=pad
            )
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.index = numpy.arange(len(self.examples))

    def __len__(self):
        """Number of examples available.

        Returns
        -------
        int
            The number of examples available.
        """
        l = super(BatchedBioIntervalSequence, self).__len__()
        return l // self.batch_size

    def __getitem__(self, item):
        """
        Indexes into the set of examples and labels.

        Parameters
        ----------
        item : int
            The index in the example/label pairs to fetch.

        Returns
        -------
        tuple(numpy.ndarray, numpy.ndarray)
            A tuple consisting of the example and the target label.

        """
        x = list()
        y = list()
        #for i in range(self.batch_size):
        #    cur_x, cur_y = self._load_unshuffled(self.index[item + i])
        for i in range(item*self.batch_size, (item+1)*self.batch_size):
            cur_x, cur_y = self._load_unshuffled(self.index[i])
            x.append(cur_x)
            y.append(cur_y)
        x = numpy.stack(x)
        y = numpy.stack(y)
        return x, y

    def on_epoch_end(self):
        """
        If applicable, shuffle the examples at the end of an epoch.
        """
        if self.shuffle:
            self.index = self.random_state.choice(len(self.examples),
                                                  len(self.examples),
                                                  replace=False)

    def close(self):
        """
        Close the file connection of Sequence
        """
        self.reference_sequence.close()


class BatchedBioIntervalSequenceGenerator(BatchedBioIntervalSequence):
    """This class modifies on top of BatchedBioIntervalSequence by performing the 
    generator loop infinitely
    """
    def __init__(self, *args, **kwargs):
        super(BatchedBioIntervalSequenceGenerator, self).__init__(*args, **kwargs)
        self.step = 0

    def __getitem__(self, item):
        x = list()
        y = list()
        self.step += 1
        if self.step == len(self) and self.shuffle:
            self._shuffle()
            print(self.step)
            self.step = 0
        for i in range(self.step*self.batch_size, (self.step+1)*self.batch_size):
            cur_x, cur_y = self._load_unshuffled(self.index[i])
            x.append(cur_x)
            y.append(cur_y)
        x = numpy.stack(x)
        y = numpy.stack(y)
        return x, y

    def _shuffle(self):
        print("Shuffled")
        self.index = self.random_state.choice(len(self.examples),
                                              len(self.examples),
                                              replace=False)

    def on_epoch_end(self):
        pass
