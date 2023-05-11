import math
import random
from abc import ABC, abstractmethod
from enum import Enum


class SimplicityTest(ABC):
    @abstractmethod
    def check(self, number: int, precision: float) -> bool:
        pass


class TestMode(Enum):
    FERMAT = 0
    SOLOVEY_STRASSEN = 1
    MILLER_RABIN = 2


class LegendreSymbol:
    def calculate(self, first: int, second: int) -> int:
        if first <= 0:
            raise ValueError("Числитель не является целым числом!")
        if second <= 2:
            raise ValueError("Знаменатель должен быть больше 2-х!")
        if not second % 2:
            raise ValueError("Знаменатель является чётным числом!")
        if not (comp := first % second):
            return 0
        if comp == 1:
            return 1
        value = 1 if not ((comp - 1) * (second - 1) >> 2 & 1) else -1
        if not comp % 2:
            return self.calculate(second % comp, comp) * value
        value = 2 if not ((second * second - 1) >> 3 & 1) else 1
        return self.calculate(comp >> 1, second) * value


class JacobiSymbol:
    def calculate(self, first: int, second: int) -> int:
        if first <= 0:
            raise ValueError("Числитель не является целым числом!")
        if second <= 1:
            raise ValueError("Знаменатель должен быть больше единицы!")
        if not second % 2:
            raise ValueError("Знаменатель является чётным числом!")
        if first == 1:
            return 1
        value = 1 if not (second >> 1 & 1) else -1
        if first < 0:
            return self.calculate(-first, second) * value
        value = 1 if not ((second * second - 1) >> 3 & 1) else -1
        if not first % 2:
            return self.calculate(first >> 1, second) * value
        value = 1 if not (((first - 1) * (second - 1)) >> 2 & 1) else -1
        return self.calculate(second % first, first) * value


class FermatTest(SimplicityTest):
    def check(self, number: int, probability: float) -> bool:
        if number < 2:
            raise ValueError("Число должно быть больше 1!")
        if number == 2:
            return True
        random_set = set()
        for i in range(math.ceil(-math.log2(1 - probability))):
            random_value = random.randint(2, number - 1)
            while random_value in random_set:
                random_value = random.randint(2, number - 1)
            if math.gcd(random_value, number) != 1 or pow(random_value, number - 1, number) != 1:
                return False
            random_set.add(random_value)
            if len(random_set) == number - 2:
                return True
        return True


class SoloveyStrassenTest(SimplicityTest):
    def check(self, number: int, probability: float) -> bool:
        if number < 2:
            raise ValueError("Число должно быть больше 1!")
        if number == 2:
            return True
        jacobi_object = JacobiSymbol()
        random_set = set()
        for i in range(math.ceil(-math.log2(1 - probability))):
            random_value = random.randint(2, number - 1)
            while random_value in random_set:
                random_value = random.randint(2, number - 1)
            if math.gcd(random_value, number) != 1 or pow(random_value, number >> 1, number) != \
                    jacobi_object.calculate(random_value, number):
                return False
            random_set.add(random_value)
            if len(random_set) == number - 2:
                return True
        return True


class MillerRabinTest(SimplicityTest):
    def check(self, number: int, probability: float) -> bool:
        if number < 2:
            raise ValueError("Число должно быть больше 1!")
        if number == 2:
            return True
        t = number - 1
        difference = 0
        while not 1 & t:
            difference += 1
            t >>= 1
        out = False
        random_set = set()
        for i in range(math.ceil(-math.log(1 - probability, 4))):
            if len(random_set) == number - 2:
                return True
            random_value = random.randint(2, number - 1)
            while random_value in random_set:
                random_value = random.randint(2, number - 1)
            x = pow(random_value, t, number)
            random_set.add(random_value)
            if x == 1 or x == number - 1:
                continue
            for j in range(difference - 1):
                x = (x * x) % number
                if x == 1:
                    return False
                if x == number - 1:
                    out = True
                    break
            if out:
                out = False
                continue
            return False
        return True
