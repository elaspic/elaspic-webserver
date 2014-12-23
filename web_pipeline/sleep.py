from random import randint
from time import sleep



sleepFor = randint(20, 30)

print 'Will sleep for', sleepFor

sleep(sleepFor)

print 'Done sleeping'