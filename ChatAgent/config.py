import os

from environs import Env
env = Env()
env.read_env()
EMAIL = env.str("email")
PASSWORD = env.str("password")