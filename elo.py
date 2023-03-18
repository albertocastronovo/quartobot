from math import ceil


def get_winning_probability(rating_1, rating_2) -> float:
    return 1.0 / (1.0 + 10.0**((rating_1 - rating_2)/400.0))


def get_next_rating(current_rating, winning_probability, won=1) -> int:
    return int(current_rating) + int(ceil(32*(won - winning_probability)))

