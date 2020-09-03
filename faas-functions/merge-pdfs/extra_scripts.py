import os
import sys
from shutil import copyfile

# replace some files of lib PyPDF2
# because bugs about charset, outline, etc will raise


if not os.path.isfile('function/generic.py'):
    sys.stderr.write('[ERROR] no fixed file generic.py!')
    exit(-1)

if not os.path.isfile('function/utils.py'):
    sys.stderr.write('[ERROR] no fixed file utils.py!')
    exit(-1)

if not os.path.isfile('function/pdf.py'):
    sys.stderr.write('[ERROR] no fixed file utils.py!')
    exit(-1)

if not os.path.isdir('/home/app/.local/lib/python3.7/site-packages/PyPDF2'):
    sys.stderr.write('[ERROR] no PyPDF2 lib!')
    exit(-1)

try:
    copyfile('function/generic.py', '/home/app/.local/lib/python3.7/site-packages/PyPDF2/generic.py')
    copyfile('function/utils.py', '/home/app/.local/lib/python3.7/site-packages/PyPDF2/utils.py')
    copyfile('function/pdf.py', '/home/app/.local/lib/python3.7/site-packages/PyPDF2/pdf.py')
except Exception as e:
    sys.stderr.write('[ERROR] copy files error: %s' % (e,))
    exit(-1)
