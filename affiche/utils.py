import random


def get_random_string(length=50,
                      allowed_chars='abcdefghijklmnopqrstuvwxyz'
                                    'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
    sys_random = random.SystemRandom()
    return ''.join(sys_random.choice(allowed_chars) for number in range(length))


def get_secret_key():
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
    return get_random_string(allowed_chars=chars)
