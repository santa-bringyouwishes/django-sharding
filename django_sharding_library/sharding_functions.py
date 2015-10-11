from itertools import cycle
from random import choice, randint


class BaseBucketingStrategy(object):
    """
    A base strategy for bucketing Users into shards. In order to extend this
    strategy, you must define a `pick_shard` and a `get_shard` method that
    both take the model that is sharded by.
    """
    def __init__(self, shard_group='default'):
        self.shard_group = shard_group

    def get_shards(self, databases):
        shards = []
        for name, config in databases.items():
            if config.get('SHARD_GROUP') == self.shard_group and not config.get('PRIMARY'):
                shards.append(name)
        return shards

    def pick_shard(self, model_sharded_by):
        """
        Returns the shard for the model which has not previously been bucketed
        into a shard.
        """
        raise NotImplemented

    def get_shard(self, model_sharded_by):
        """
        Returns the shard for a model which has already been assigned a shard.
        """
        raise NotImplemented


class BaseShardedModelBucketingStrategy(BaseBucketingStrategy):
    """
    A base strategy for bucketing models into shards when saving the shard on
    the model.
    """
    def get_shard(self, model_sharded_by):
        return model_sharded_by.shard


class RoundRobinBucketingStrategy(BaseShardedModelBucketingStrategy):
    """
    A shard selection strategy that assigns shards in a round-robin way.
    This is non-deterministic and this strategy assumes the shard is saved to
    the model.
    """
    def __init__(self, shard_group, databases):
        super(RoundRobinBucketingStrategy, self).__init__(shard_group)
        shards = self.get_shards(databases)
        # To help balance out the fact that this would start the round-robin
        # bucketing at initialization time, we start at a random index.
        max_index = max(0, len(shards) - 1)
        starting_index = randint(0, max_index)
        shards = shards[starting_index:] + shards[:starting_index]
        self._shards_cycle = cycle(shards)

    def pick_shard(self, model_sharded_by):
        return self._shards_cycle.next()


class RandomBucketingStrategy(BaseShardedModelBucketingStrategy):
    """
    A shard selection strategy that assigns shards randomly.
    This is non-deterministic and this strategy assumes the shard is saved to
    the model.
    """
    def __init__(self, shard_group, databases):
        super(RoundRobinBucketingStrategy, self).__init__(shard_group)
        self.shards = self.get_shards(databases)

    def pick_shard(self, model_sharded_by):
        return choice(self.shards)


class ModBucketingStrategy(BaseBucketingStrategy):
    """
    A shard selection strategy that assigns shards based on the mod of the
    models pk.
    Note: It is only deterministic as long as the number of shards do not
    change.
    """
    def __init__(self, shard_group, databases):
        super(RoundRobinBucketingStrategy, self).__init__(shard_group)
        self.shards = self.get_shards(databases)

    def pick_shard(self, model_sharded_by):
        self.shards[hash(str(model_sharded_by.pk)) % len(self.shards)]

    def get_shard(self, model_sharded_by):
        self.shards[hash(str(model_sharded_by.pk)) % len(self.shards)]


class SavedModBucketingStrategy(BaseShardedModelBucketingStrategy, ModBucketingStrategy):
    """
    A shard selection strategy that assigns shards based on the mod of the
    models pk.
    This is non-deterministic and this strategy assumes the shard is saved to
    the model. It is non-deterministic as the number of shards may change.
    """
    pass