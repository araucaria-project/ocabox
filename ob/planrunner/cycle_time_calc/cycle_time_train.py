from typing import Dict, Any, List

import numpy as np
from sklearn.linear_model import LinearRegression
from ob.planrunner.cycle_time_calc.abstract_cycle_time import AbstractCycleTime
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

import logging


logger = logging.getLogger(__name__.rsplit('.')[-1])


class CycleTimeTrain(AbstractCycleTime):
    """
    This class represent cycle time trainer
    """



    def __init__(self, telescope_name: str):
        self.data_x: np.array or None = None
        self.data_y: np.array or None = None
        self.r2: float or None = None
        self.coef: List[float] or None = None
        self.intercept: float or None = None
        super().__init__(telescope_name=telescope_name)
        self.x_columns: List[str] = self.DATA_CLEAN_ORDER[4:]
        self.y_column: str = self.DATA_CLEAN_ORDER[3]

    def read_data_from_file(self, command: str or None = None):
        self._data = self.read_file(self.base_folder, self.clean_data_file_name(command=command))

    def build_array(self, xory: str):
        if xory == 'x':
            w = self.x_columns
        elif xory == 'y':
            w = self.y_column
        else:
            w = []
        l1 = []
        for n in self.data_list:
            l2 = []
            for p, q in n.items():
                if p in w:
                    l2.append(q)
            l1.append(l2)
        if xory == 'x':
            self.data_x = np.asarray(l1)
        elif xory == 'y':
            self.data_y = np.asarray(l1)
        else:
            pass

    def train_data_comm(self, command: str):
        self.read_data_from_file(command=command)
        self.parse_data()
        self.build_array('x')
        self.build_array('y')
        self.train()

    def train(self):
        model = LinearRegression()
        x_train, x_test, y_train, y_test = train_test_split(self.data_x, self.data_y, random_state=123, test_size=0.3)
        model.fit(x_train, y_train)
        y_pred = model.predict(x_test)
        self.r2 = r2_score(y_test, y_pred)
        self.coef = model.coef_
        self.intercept = model.intercept_


if __name__ == '__main__':
    c = CycleTimeTrain('dev', )
    c.train_data_comm('OBJECT')
    print(c.data_list)
    print(c.data_x)
    print(c.data_y)
    print(c.r2)
    print(c.coef)
    print(c.intercept)
