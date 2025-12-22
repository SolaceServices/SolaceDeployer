from enum import Enum, IntEnum

class Environment(Enum):
    DEV = 'dev'
    TST = 'tst'
    ACC = 'acc'
    PRD = 'prd'

class Action(Enum):
    DEPLOY = 'deploy'
    UNDEPLOY = 'undeploy'
    SAVE = 'save'

class State(IntEnum):
    DRAFT = 1
    RELEASED = 2
    DEPRECATED = 3
    RETIRED = 4

    @classmethod
    def from_value(cls, value):
        return cls(int(value))

    @property
    def label(self):
        return self.name.lower()

class Mode(Enum):
    CONFIG_PUSH = 'configPush'
    SEMP = 'semp'
