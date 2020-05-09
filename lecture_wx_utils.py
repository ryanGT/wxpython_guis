import re
import lecture_utils
import os

p1 = re.compile('^ME_*([0-9]+)_lecture_([0-9]+)_')

git_dir = '/Users/rkrauss/git/wxpython_guis/'

semester_root = '/Users/rkrauss/siue/classes/Fall_2015/'

course_roots = {'107':'/Users/kraussry/gdrive_teaching/107_W19', \
                '345':'/Users/kraussry/gdrive_teaching/345_F19', \
                '445':'/Users/kraussry/gdrive_teaching/445_SS19', \
                '445/545':'/Users/kraussry/gdrive_teaching/445_SS19', \
                }


lecture_roots = {}

for key, value in course_roots.items():
    lfolder = os.path.join(value, 'lectures')
    lecture_roots[key] = lfolder
    

lab_root = '/Users/kraussry/gdrive_teaching/345_F18/lab/'

course_class_dict = {}



